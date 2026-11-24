#!/usr/bin/env python3
"""Read-only enuma OTA and target-files checks. This is not a device boot test."""
import argparse
import base64
import hashlib
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path

CHUNK = 4 * 1024 * 1024
BOOT_IMAGES = {'boot': b'ANDROID!', 'vendor_boot': b'VNDRBOOT',
               'dtbo': b'\xd7\xb7\xab\x1e', 'vbmeta': b'AVB0'}
# BoardConfigCommon.mk, web1n sm8250-common pin 3c71874002bd93b1c883c946064d5153fc9d7f69.
# Do not distribute OTA packages that rewrite bootloader/radio firmware.
OTA_PARTITIONS = frozenset({'boot', 'dtbo', 'odm', 'product', 'system', 'system_ext',
                            'vbmeta', 'vbmeta_system', 'vendor', 'vendor_boot'})


def require(ok, message):
    if not ok:
        raise ValueError(message)


def parse_properties(raw):
    result = {}
    for line in raw.decode('ascii').splitlines():
        if not line:
            continue
        key, value = line.split('=', 1)
        require(key not in result, f'duplicate property: {key}')
        result[key] = value
    return result


def sha256_stream(stream, initial=b''):
    h = hashlib.sha256(initial)
    for chunk in iter(lambda: stream.read(CHUNK), b''):
        h.update(chunk)
    return h


def read_small(z, name):
    require(z.getinfo(name).file_size <= 1024 * 1024, f'oversized properties: {name}')
    return z.read(name)


def verify_outer_signature(ota, cert):
    size = ota.stat().st_size
    with ota.open('rb') as f:
        f.seek(-6, 2)
        signature_start, marker, comment_len = struct.unpack('<H2sH', f.read(6))
        require(marker == b'\xff\xff' and 6 < signature_start <= comment_len < size - 22,
                'invalid AOSP OTA signature footer')
        f.seek(size - comment_len - 22)
        eocd = f.read(22)
        require(eocd.startswith(b'PK\x05\x06') and int.from_bytes(eocd[-2:], 'little') == comment_len,
                'invalid signed zip directory footer')
        f.seek(size - signature_start)
        signature = f.read(signature_start - 6)
        f.seek(0)
        with tempfile.TemporaryDirectory(prefix='enuma-ota-') as temp:
            der = Path(temp) / 'footer.der'
            der.write_bytes(signature)
            cmd = ['openssl', 'cms', '-verify', '-binary', '-inform', 'DER', '-in', str(der),
                   '-content', '/dev/stdin', '-nointern', '-certfile', str(cert), '-noverify', '-out', '/dev/null']
            remaining = size - comment_len - 2
            with subprocess.Popen(cmd, stdin=subprocess.PIPE) as openssl:
                try:
                    while remaining:
                        data = f.read(min(remaining, CHUNK))
                        require(data, 'unexpected EOF in signed OTA body')
                        openssl.stdin.write(data)
                        remaining -= len(data)
                except BrokenPipeError:
                    pass
                finally:
                    try:
                        openssl.stdin.close()
                    except BrokenPipeError:
                        pass
                require(openssl.wait() == 0 and remaining == 0, 'OTA signature failed against expected cert')


def proto_fields(data):
    """Read the primitive fields used by AOSP system/update_engine/update_metadata.proto."""
    def varint(pos):
        value = 0
        for shift in range(0, 64, 7):
            require(pos < len(data), 'truncated payload protobuf varint')
            byte = data[pos]
            pos += 1
            require(shift < 63 or byte <= 1, 'overflow in payload protobuf varint')
            value |= (byte & 0x7f) << shift
            if byte < 128:
                return value, pos
        raise ValueError('invalid payload protobuf varint')

    pos = 0
    while pos < len(data):
        tag, pos = varint(pos)
        field, wire = tag >> 3, tag & 7
        require(0 < field < 2**29, 'invalid payload protobuf field number')
        if wire == 0:
            value, pos = varint(pos)
        elif wire in (1, 2, 5):
            if wire == 2:
                size, pos = varint(pos)
            else:
                size = 8 if wire == 1 else 4
            require(size <= len(data) - pos, 'truncated payload protobuf field')
            value, pos = data[pos:pos + size], pos + size
        else:
            raise ValueError(f'unexpected payload protobuf wire type: {wire}')
        yield field, wire, value


def proto_item(fields, field, wire, default=None):
    matches = [(w, value) for k, w, value in fields if k == field]
    if not matches:
        require(default is not None, f'missing payload protobuf field {field}')
        return default
    require(len(matches) == 1 and matches[0][0] == wire,
            f'duplicate or malformed payload protobuf field {field}')
    return matches[0][1]


def parse_boot_partitions(manifest):
    # DeltaArchiveManifest: block_size=3, minor_version=12, partitions=13.
    # PartitionUpdate: partition_name=1, new_partition_info=7.
    # PartitionInfo: size=1, hash=2. Full payload uses minor_version 0.
    fields = list(proto_fields(memoryview(manifest)))
    block = proto_item(fields, 3, 0, 4096)
    require(block == 4096, f'unexpected OTA payload block size: {block}')
    require(proto_item(fields, 12, 0, 0) == 0, 'expected full payload minor version 0')
    images, names = {}, set()
    for field, wire, val in fields:
        if field != 13:
            continue
        require(wire == 2, 'invalid OTA partition update')
        part = list(proto_fields(val))
        name = bytes(proto_item(part, 1, 2)).decode('ascii')
        require(name in OTA_PARTITIONS, f'unexpected OTA partition: {name!r}')
        require(name not in names, f'duplicate OTA partition: {name}')
        names.add(name)
        info = list(proto_fields(proto_item(part, 7, 2)))
        size, digest = proto_item(info, 1, 0), bytes(proto_item(info, 2, 2))
        require(size > 0 and size % block == 0 and len(digest) == 32,
                f'invalid OTA partition size or hash: {name}')
        if name in BOOT_IMAGES:
            images[name] = (size, digest)
    require(names == OTA_PARTITIONS, f'missing OTA partitions: {sorted(OTA_PARTITIONS - names)}')
    print('A/B partition set matches enuma; modem and bootloader partitions are excluded')
    return block, images


def verify_payload(z, props):
    item = z.getinfo('payload.bin')
    require(item.compress_type == zipfile.ZIP_STORED, 'payload.bin is not stored')
    require(int(props['FILE_SIZE']) == item.file_size, 'payload FILE_SIZE mismatch')
    with z.open(item) as f:
        header = f.read(24)
        magic, version, manifest_size, signature_size = struct.unpack('>4sQQI', header)
        require(magic == b'CrAU' and version == 2, 'payload is not a v2 A/B update')
        # update_engine hashes the header and manifest here, excluding the
        # following signature block. FILE_HASH still covers the entire payload.
        metadata_size = len(header) + manifest_size
        signed_prefix_size = metadata_size + signature_size
        require(manifest_size > 0 and signature_size > 0 and metadata_size == int(props['METADATA_SIZE'])
                and signed_prefix_size <= 32 * 1024 * 1024 and signed_prefix_size < item.file_size, 'invalid payload metadata size')
        manifest = f.read(manifest_size)
        require(len(manifest) == manifest_size, 'truncated payload manifest')
        metadata = header + manifest
        require(base64.b64encode(hashlib.sha256(metadata).digest()).decode() == props['METADATA_HASH'], 'payload METADATA_HASH mismatch')
        require(base64.b64encode(sha256_stream(f, metadata).digest()).decode() == props['FILE_HASH'], 'payload FILE_HASH mismatch')
        boot_metadata = parse_boot_partitions(manifest)
    print(f'A/B payload: {item.file_size:,} bytes; metadata and payload hashes match')
    return boot_metadata


def verify_target_files(path, product_out, boot_metadata):
    block, partitions = boot_metadata
    with zipfile.ZipFile(path) as tf:
        names = tf.namelist()
        required = ('/Phonesky.apk', '/GoogleServicesFramework.apk', '/LMOFreeform.apk',
                    '/LMOFreeformSidebar.apk', '/MiPadParts.apk', '/stylus-bridge',
                    '/android.software.freeform_window_management.xml')
        for suffix in required:
            require(any(n.endswith(suffix) and tf.getinfo(n).file_size > 0 for n in names),
                    f'not present in target files: {suffix}')
        require(any('/apex/' in n and n.endswith(('.apex', '.capex')) and 'com.google.android.gmssystem.prodvic' in n
                    for n in names), 'Google services APEX missing')
        for part, magic in BOOT_IMAGES.items():
            filename = f'{part}.img'
            path = product_out / filename
            with path.open('rb') as raw, tf.open(f'IMAGES/{filename}') as packed:
                header = raw.read(len(magic))
                require(header == magic, f'{filename} has unexpected magic')
                hashed = sha256_stream(raw, header)
                require(hashed.digest() == sha256_stream(packed).digest(), f'{filename} differs from target files')
                padding = (-raw.tell()) % block
                size, expected_hash = partitions[part]
                require(size == raw.tell() + padding, f'{filename} size differs from OTA partition')
                # AOSP generate_delta_main.cc RoundUpPartitions extends with zero bytes.
                hashed.update(bytes(padding))
                require(hashed.digest() == expected_hash, f'{filename} SHA-256 differs from OTA partition')
            print(f'Image {filename}: target-files and OTA payload SHA-256 match')
    print('Target files: GMS Core + Play Store, sidebar/freeform and pen bridge present')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ota', type=Path)
    p.add_argument('target_files', type=Path)
    p.add_argument('product_out', type=Path)
    p.add_argument('--cert', type=Path, required=True, help='expected OTA signing certificate in PEM')
    args = p.parse_args()
    try:
        with zipfile.ZipFile(args.ota) as ota:
            names = ota.namelist()
            require(len(names) == len(set(names)), 'duplicate OTA zip entries')
            require('META-INF/com/google/android/updater-script' not in names,
                    'unexpected legacy updater-script in A/B OTA')
            metadata = parse_properties(read_small(ota, 'META-INF/com/android/metadata'))
            require(metadata.get('pre-device') == 'enuma', 'OTA pre-device is not enuma-only')
            require(metadata.get('ota-type') == 'AB', 'OTA is not A/B')
            require('pre-build' not in metadata and 'pre-build-incremental' not in metadata, 'expected full OTA, not an incremental')
            boot_metadata = verify_payload(ota, parse_properties(read_small(ota, 'payload_properties.txt')))
        verify_outer_signature(args.ota, args.cert)
        verify_target_files(args.target_files, args.product_out, boot_metadata)
    except (ValueError, OSError, KeyError, struct.error, zipfile.BadZipFile) as exc:
        p.exit(1, f'FAIL: {exc}\n')
    print('PASS: enuma OTA static artifact checks. No claim of physical-device operation.')


if __name__ == '__main__':
    main()
