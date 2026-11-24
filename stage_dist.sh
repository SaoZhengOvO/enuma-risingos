#!/usr/bin/env bash
set -euo pipefail
umask 022
shopt -s nullglob
cd /build/src
product=$(realpath -- "${OUT_DIR:-out}/target/product/enuma")
cert=${ENUMAROM_OTA_CERT:?Expected OTA signer certificate is missing}
[[ -r "$cert" && -s /build/logs/resolved-manifest.xml ]]
if [[ $# == 1 ]]; then
    ota=$(realpath "$1")
    [[ $(dirname "$ota") == "$product" && $(basename "$ota") == RisingOS-*CORE*enuma.zip ]]
else
    otas=("$product"/RisingOS-*CORE*enuma.zip)
    [[ ${#otas[@]} == 1 ]] || { printf 'Expected one enuma CORE OTA, found %s\n' "${#otas[@]}" >&2; exit 1; }
    ota=${otas[0]}
fi
target_files=("$product"/obj/PACKAGING/target_files_intermediates/lineage_enuma-target_files*.zip)
[[ ${#target_files[@]} == 1 ]] || { printf 'Expected one enuma target files package, found %s\n' "${#target_files[@]}" >&2; exit 1; }
work=$(mktemp -d /build/dist/.enuma-check.XXXXXXXX)
trap 'rm -rf -- "$work"' EXIT
python3 /build/verify_enuma_dtbo.py "$product/dtbo.img" 2>&1 | tee "$work/verification.log"
python3 /build/verify_ota.py "$ota" "${target_files[0]}" "$product" --cert "$cert" 2>&1 | tee -a "$work/verification.log"
case "$cert" in
    */target/product/security/testkey.x509.pem) tag=public-test-key ;;
    *) tag=check-key-provenance ;;
esac
stage=/build/dist/"$(basename "$ota" .zip)-${tag}-UNTESTED"
[[ ! -e "$stage" ]]
cp --reflink=auto -- "$ota" "$work/"
for image in boot.img vendor_boot.img dtbo.img vbmeta.img; do cp --reflink=auto -- "$product/$image" "$work/"; done
cp -- /build/logs/resolved-manifest.xml /build/enuma-core.patch /build/soong-memory-env.patch "$cert" "$work/"
printf 'Device: enuma only\nSigning: %s\nVerification: static only; no hardware test\n' "$tag" > "$work/STATUS.txt"
( cd "$work"; sha256sum -- *.zip *.img *.xml *.patch *.pem STATUS.txt verification.log > SHA256SUMS; sha256sum --check SHA256SUMS )
mv -- "$work" "$stage"
trap - EXIT
printf 'Artifacts staged (hardware untested): %s\n' "$stage"
