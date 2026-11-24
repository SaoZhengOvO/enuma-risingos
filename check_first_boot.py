#!/usr/bin/env python3
"""Read-only smoke check for an already booted enuma RisingOS Google Core device."""
import argparse
import subprocess


PACKAGES = {
    'Google Play Store': 'com.android.vending',
    'Google Play services': 'com.google.android.gms',
    'LMO floating windows': 'com.libremobileos.freeform',
    'LMO sidebar': 'com.libremobileos.sidebar',
    'Xiaomi Pad settings': 'org.lineageos.pad_parts',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default='adb', help='path to Android Platform Tools adb')
    parser.add_argument('--serial', help='target adb serial; otherwise select one USB device')
    args = parser.parse_args()
    cmd = [args.adb, '-s', args.serial] if args.serial else [args.adb, '-d']

    def read(*words):
        result = subprocess.run([*cmd, *words], text=True, capture_output=True, timeout=15)
        if result.returncode:
            message = result.stderr.strip() or result.stdout.strip() or f'exit {result.returncode}'
            raise ValueError(f'adb {" ".join(words)}: {message}')
        return result.stdout.strip()

    def prop(name):
        return read('shell', 'getprop', name)

    try:
        state = read('get-state')
        if state != 'device':
            raise ValueError(f'ADB device state is {state!r}, expected device')
        model = prop('ro.product.device')
        if model != 'enuma':
            raise ValueError(f'not the target device: ro.product.device={model!r}')
        if prop('sys.boot_completed') != '1':
            raise ValueError('Android has not completed boot yet')
        rising = prop('ro.rising.build.version')
        kind = prop('ro.rising.packagetype')
        if not rising or kind != 'CORE' or prop('ro.rising.device') != 'enuma':
            raise ValueError('the running build does not identify as RisingOS enuma Google Core')
        print(f'Boot completed on enuma: {rising} (CORE)')
        features = set(read('shell', 'pm', 'list', 'features').splitlines())
        if 'feature:android.software.freeform_window_management' not in features:
            raise ValueError('Android does not report the freeform-window feature')
        print('Freeform-window feature present')
        for label, package in PACKAGES.items():
            locations = read('shell', 'pm', 'path', package)
            if not any(line.startswith('package:') and line.endswith('.apk') for line in locations.splitlines()):
                raise ValueError(f'package not visible: {label} ({package})')
            print(f'Package present: {label} ({package})')
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f'FAIL: {error}\n')
    print('PASS: boot and package inventory. Google login, pen pressure/buttons, floating-window actions and stability require manual tests.')


if __name__ == '__main__':
    main()
