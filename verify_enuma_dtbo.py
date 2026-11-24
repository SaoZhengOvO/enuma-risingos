#!/usr/bin/env python3
"""Check that the candidate DTBO contains the enabled enuma NovaTek pen node."""
import argparse
from pathlib import Path
import struct
import zlib

MAX_IMAGE = 64 * 1024 * 1024
MAX_DTB = 16 * 1024 * 1024
MODEL = b'Qualcomm Technologies, Inc. xiaomi enuma\0'
BOARD_ID = struct.pack('>II', 46, 0)
KEEP = {b'model', b'qcom,board-id', b'compatible', b'status', b'novatek,pen-support'}


def ensure(condition, message):
    if not condition:
        raise ValueError(message)


def unpack_tree(raw):
    magic, total, off_struct, off_strings, _, version, _, _, strings_len, struct_len = struct.unpack_from('>10I', raw)
    ensure(magic == 0xd00dfeed and version >= 17 and 40 <= total <= len(raw), 'invalid FDT header')
    ensure(40 <= off_struct <= total - struct_len and 40 <= off_strings <= total - strings_len,
           'FDT block outside its tree')
    strings = raw[off_strings:off_strings + strings_len]
    end = off_struct + struct_len
    stack, nodes = [], {}
    pos = off_struct
    while pos + 4 <= end:
        token = struct.unpack_from('>I', raw, pos)[0]
        pos += 4
        if token == 1:  # FDT_BEGIN_NODE
            stop = raw.find(b'\0', pos, end)
            ensure(stop >= 0, 'unterminated FDT node name')
            name = raw[pos:stop]
            ensure(bool(name) == bool(stack) and b'/' not in name, 'invalid FDT node name')
            stack.append(name)
            node = tuple(stack)
            ensure(node not in nodes, 'duplicate FDT node')
            nodes[node] = {}
            pos = (stop + 4) & ~3
        elif token == 2:  # FDT_END_NODE
            ensure(bool(stack), 'unbalanced FDT node')
            stack.pop()
        elif token == 3:  # FDT_PROP
            ensure(bool(stack) and pos + 8 <= end, 'invalid FDT property header')
            size, nameoff = struct.unpack_from('>2I', raw, pos)
            pos += 8
            stop = strings.find(b'\0', nameoff)
            ensure(stop >= 0 and pos + size <= end, 'invalid FDT property size or name')
            name = strings[nameoff:stop]
            if name in KEEP:
                node = nodes[tuple(stack)]
                ensure(name not in node, 'duplicate relevant FDT property')
                node[name] = raw[pos:pos + size]
            pos = (pos + size + 3) & ~3
        elif token == 4:  # FDT_NOP
            continue
        elif token == 9:  # FDT_END
            ensure(not stack and (b'',) in nodes, 'incomplete FDT root')
            return nodes
        else:
            raise ValueError(f'unknown FDT token: {token}')
    raise ValueError('missing FDT_END')


def inspect_dtbo(data):
    magic, total, head_size, entry_size, count, off, _, version = struct.unpack_from('>8I', data)
    ensure(magic == 0xd7b7ab1e and version in (0, 1), 'unsupported Android DTBO table')
    ensure(32 <= head_size <= off and entry_size >= 32 and 0 < count <= 1024,
           'invalid Android DTBO entry table')
    bound = off + count * entry_size
    ensure(bound <= total <= len(data), 'truncated Android DTBO table')
    enuma_count = 0
    for idx in range(count):
        size, offset, _, _, flags = struct.unpack_from('>5I', data, off + idx * entry_size)
        ensure(0 < size <= MAX_DTB and bound <= offset <= total - size, f'invalid DTBO entry {idx}')
        raw = data[offset:offset + size]
        compression = (flags & 0x0f) if version == 1 else 0
        if compression in (1, 2):
            inflater = zlib.decompressobj(15 if compression == 1 else 31)
            raw = inflater.decompress(raw, MAX_DTB + 1)
            ensure(inflater.eof and len(raw) <= MAX_DTB, f'invalid compressed DTBO entry {idx}')
        else:
            ensure(compression == 0, f'unknown DTBO compression in entry {idx}')
        nodes = unpack_tree(raw)
        root = nodes[(b'',)]
        if root.get(b'model') != MODEL:
            continue
        ensure(root.get(b'qcom,board-id') == BOARD_ID, f'enuma board ID differs in entry {idx}')
        pen_paths = [path for path, props in nodes.items()
                     if b'novatek,NVT-ts-spi' in props.get(b'compatible', b'').split(b'\0')
                     and props.get(b'novatek,pen-support') == b''
                     and props.get(b'status', b'okay\0') in {b'ok\0', b'okay\0'}]
        ensure(bool(pen_paths), f'enuma NovaTek pen node missing or disabled in entry {idx}')
        enuma_count += 1
        print(f'DTBO entry {idx}: enuma board 46, enabled NovaTek pen at '
              + ', '.join(b'/'.join(p).decode('ascii', 'replace') for p in pen_paths))
    ensure(enuma_count > 0, 'DTBO contains no enuma overlay')
    return enuma_count, count


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dtbo', type=Path)
    args = p.parse_args()
    try:
        with args.dtbo.open('rb') as f:
            data = f.read(MAX_IMAGE + 1)
        ensure(len(data) <= MAX_IMAGE, 'DTBO image exceeds device size limit')
        enuma, count = inspect_dtbo(data)
    except (ValueError, OSError, struct.error, zlib.error) as exc:
        p.exit(1, f'FAIL: {exc}\n')
    print(f'PASS: enuma NovaTek pen node enabled in {enuma}/{count} overlays (hardware untested).')


if __name__ == '__main__':
    main()
