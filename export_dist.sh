#!/usr/bin/env bash
# Run on the host after build.sh has exited 0; pass its printed staging directory.
set -euo pipefail
umask 022
stage=${1:?Usage: bash export_dist.sh /build/dist/RisingOS-…-UNTESTED [destination]}
[[ "$stage" =~ ^/build/dist/(RisingOS-[[:alnum:]_.-]+-UNTESTED)$ ]] || { echo 'Invalid OTA staging directory' >&2; exit 1; }
name=${BASH_REMATCH[1]}
container=${ENUMAROM_BUILD_CONTAINER:-enuma-risingos-compile}
[[ $(docker inspect --format '{{.State.Status}} {{.State.ExitCode}}' "$container") == 'exited 0' ]] || { echo 'Build has not exited successfully' >&2; exit 1; }
base=$(cd -- "$(dirname -- "$0")" && pwd)
out=$(realpath -m -- "${2:-$base/dist}")
final=$out/$name
[[ ! -e "$final" && ! -L "$final" ]] || { echo "Destination already exists: $final" >&2; exit 1; }
mkdir -p -- "$out"
work=$(mktemp -d -- "$out/.incoming.XXXXXXXX")
trap 'rm -rf -- "$work"' EXIT
docker cp "$container:$stage/." "$work/"
(
    cd -- "$work"
    shopt -s nullglob
    otas=(RisingOS-*CORE*enuma.zip)
    certs=(*.x509.pem)
    [[ ${#otas[@]} == 1 && ${#certs[@]} == 1 ]]
    [[ ${name#"${otas[0]%.zip}"-} =~ ^(public-test-key|check-key-provenance)-UNTESTED$ ]]
    files=("${otas[0]}" "${certs[0]}" boot.img vendor_boot.img dtbo.img vbmeta.img resolved-manifest.xml enuma-core.patch soong-memory-env.patch STATUS.txt verification.log)
    for file in "${files[@]}" SHA256SUMS; do [[ -f "$file" && ! -L "$file" && -s "$file" ]]; done
    # The host's inherited NAS ACL can clear the requested mode on copied files.
    chmod 0644 -- "${files[@]}" SHA256SUMS
    listed=$(awk 'length($1) != 64 || $1 ~ /[^0-9a-f]/ || substr($0,65,2) != "  " { exit 1 } { print substr($0,67) }' SHA256SUMS | LC_ALL=C sort)
    diff -u <(printf '%s\n' "${files[@]}" | LC_ALL=C sort) <(printf '%s\n' "$listed")
    sha256sum --check --strict SHA256SUMS
    grep -Fxq 'PASS: enuma OTA static artifact checks. No claim of physical-device operation.' verification.log
)
chmod 0755 -- "$work"
mv -T --no-clobber -- "$work" "$final"
[[ ! -e "$work" ]] || { echo "Destination appeared during export: $final" >&2; exit 1; }
trap - EXIT
printf 'Verified host export (hardware untested): %s\n' "$final"
