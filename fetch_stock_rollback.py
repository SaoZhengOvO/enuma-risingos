#!/usr/bin/env python3
"""Fetch the enuma stock rollback archive with restartable, checked byte ranges."""
import argparse
import concurrent.futures
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time

NAME = 'enuma_images_OS1.0.3.0.TKZCNXM_20240508.0000.00_13.0_cn_fc06cc99cc.tgz'
URL = f'https://cdnorg.d.miui.com/OS1.0.3.0.TKZCNXM/{NAME}'
SIZE = 5_411_798_301
MD5 = 'fc06cc99cc67649c61917638667ae67c'
BLOCK = 32 * 1024 * 1024
NEEDED = ('/flash_all.sh', '/images/boot.img', '/images/vendor_boot.img', '/images/super.img')


def fetch(url, size, path, start, end):
    length = end - start + 1
    if path.is_file() and path.stat().st_size == length:
        return 'cached'
    work = path.with_suffix('.tmp')
    headers = path.with_suffix('.headers.tmp')
    wanted = f'bytes {start}-{end}/{size}'
    for attempt in range(1, 6):
        try:
            result = subprocess.run([
                'curl', '--proto', '=https', '--proto-redir', '=https',
                '--fail', '--silent', '--show-error', '--location', '--max-redirs', '3',
                '--connect-timeout', '12', '--max-time', '360', '--max-filesize', str(length),
                '--range', f'{start}-{end}', '--dump-header', str(headers),
                '--output', str(work), '--write-out', '%{http_code}', url,
            ], capture_output=True, text=True, timeout=370)
            if result.returncode:
                raise ValueError(f'curl exit {result.returncode}: {result.stderr.strip()}')
            blocks = re.split(r'(?m)^HTTP/[^\n]*\n', headers.read_text(encoding='latin-1'))
            received = re.findall(r'(?im)^content-range:[ \t]*([^\n]+)$', blocks[-1])
            if result.stdout.strip() != '206' or received != [wanted]:
                raise ValueError(f'HTTP {result.stdout.strip()}, range {received!r}; expected {wanted!r}')
            if work.stat().st_size != length:
                raise ValueError('downloaded range has the wrong length')
            work.replace(path)
            return 'fetched'
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            work.unlink(missing_ok=True)
            print(f'range {start}-{end}: try {attempt}/5: {exc}', flush=True)
            if attempt == 5:
                raise
            time.sleep(2 ** attempt)
        finally:
            headers.unlink(missing_ok=True)


def ranges(url, size, parts, prefix, jobs, block=BLOCK):
    parts.mkdir(exist_ok=True)
    items = [(parts / f'{start:012d}', start, min(size, start + block) - 1)
             for start in range(0, size, block)]
    if prefix and prefix.is_file():
        prefix_size = prefix.stat().st_size
        resumed = 0
        with prefix.open('rb') as previous:
            for path, start, end in items:
                if end >= prefix_size:
                    break
                length = end - start + 1
                if path.is_file() and path.stat().st_size == length:
                    continue
                previous.seek(start)
                data = previous.read(length)
                if len(data) != length:
                    raise ValueError('legacy prefix changed while reading')
                work = path.with_suffix('.tmp')
                work.write_bytes(data)
                work.replace(path)
                resumed += length
        print(f'Imported {resumed} bytes from the previous download', flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        pending = {pool.submit(fetch, url, size, name, lo, hi): (lo, hi)
                   for name, lo, hi in items}
        done_bytes = 0
        for future in concurrent.futures.as_completed(pending):
            lo, hi = pending[future]
            method = future.result()
            done_bytes += hi - lo + 1
            if method != 'cached':
                print(f'Range {lo}-{hi}: {done_bytes}/{size} verified-length bytes', flush=True)
    return [name for name, _, _ in items]


def verify(path, size, expected_md5):
    if path.stat().st_size != size:
        raise ValueError('wrong assembled archive size')
    md5, sha = hashlib.md5(usedforsecurity=False), hashlib.sha256()
    with path.open('rb') as source:
        for data in iter(lambda: source.read(4 * 1024 * 1024), b''):
            md5.update(data)
            sha.update(data)
    if md5.hexdigest() != expected_md5:
        raise ValueError(f'archive MD5 {md5.hexdigest()} does not match {expected_md5}')
    names = []
    with tarfile.open(path, 'r|gz') as archive:
        for member in archive:
            if member.isfile():
                names.append(member.name)
    for suffix in NEEDED:
        if sum(name.endswith(suffix) for name in names) != 1:
            raise ValueError(f'stock archive missing or duplicates {suffix}')
    return sha.hexdigest(), names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--jobs', type=int, choices=range(1, 5), default=3)
    args = parser.parse_args()
    root = args.directory
    root.mkdir(parents=True, exist_ok=True)
    release = root / NAME
    candidate = root / (NAME + '.assembling')
    if not release.is_file():
        parts = ranges(URL, SIZE, root / 'ranges-v1', root / (NAME + '.part'), args.jobs)
        with candidate.open('wb') as output:
            for part in parts:
                with part.open('rb') as source:
                    shutil.copyfileobj(source, output, 2 * 1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
    raw = release if release.is_file() else candidate
    sha, names = verify(raw, SIZE, MD5)
    if raw == candidate:
        candidate.replace(release)
    (root / 'SHA256SUMS.tmp').write_text(f'{sha}  {NAME}\n')
    (root / 'SHA256SUMS.tmp').replace(root / 'SHA256SUMS')
    (root / 'contents.txt').write_text('\n'.join(names) + '\n')
    print(f'PASS {NAME}, {SIZE} bytes, MD5 {MD5}, SHA-256 {sha}', flush=True)


if __name__ == '__main__':
    main()
