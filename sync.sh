#!/usr/bin/env bash
set -euo pipefail
umask 022
export GIT_TERMINAL_PROMPT=0 GIT_LFS_SKIP_SMUDGE=1
export GIT_CONFIG_COUNT=3 GIT_CONFIG_KEY_0=http.version GIT_CONFIG_VALUE_0=HTTP/1.1
export GIT_CONFIG_KEY_1=user.name GIT_CONFIG_VALUE_1='Enuma ROM build'
export GIT_CONFIG_KEY_2=user.email GIT_CONFIG_VALUE_2='enuma-build@localhost'
mkdir -p /build/bin /build/src /build/logs
cd /build/src
if [[ ! -s /build/bin/repo ]]; then
  curl --proto '=https' -fsSL --retry 3 --max-time 90 https://storage.googleapis.com/git-repo-downloads/repo -o /build/bin/repo.part
  python3 -m py_compile /build/bin/repo.part
  mv /build/bin/repo.part /build/bin/repo
fi
repo() { python3 /build/bin/repo "$@"; }
exec > >(tee -a /build/logs/sync.log) 2>&1
printf '\n=== sync start %s ===\n' "$(date -Is)"
repo init --repo-url=https://github.com/GerritCodeReview/git-repo --repo-rev=stable \
  -u https://github.com/RisingOS-Revived/android -b ecb587a4b0d36e65a3eb795c9b92cbbafa58ccce \
  --manifest-upstream-branch=seventeen --partial-clone --clone-filter=blob:none \
  --no-clone-bundle --no-use-superproject --git-lfs
expected=ecb587a4b0d36e65a3eb795c9b92cbbafa58ccce
actual=$(git -C .repo/manifests rev-parse HEAD)
[[ "$actual" == "$expected" ]] || { printf 'Manifest commit mismatch: %s\n' "$actual" >&2; exit 1; }
mkdir -p .repo/local_manifests
cp /build/enuma.xml .repo/local_manifests/enuma.xml
if [[ -s /build/resolved-manifest.xml ]]; then
  repo manifest -o /build/logs/requested-manifest.xml
  python3 /build/lock_manifest.py /build/resolved-manifest.xml /build/logs/requested-manifest.xml \
    --overlay .repo/local_manifests/zz-enuma-lock.xml
  repo manifest -o /build/logs/locked-requested-manifest.xml
  python3 /build/lock_manifest.py /build/resolved-manifest.xml /build/logs/locked-requested-manifest.xml
fi
repo manifest --no-local-manifests -o /build/logs/upstream.xml
repo list -a > /build/logs/project-list.txt
sed -n '/device\/xiaomi\/enuma :/p; /vendor\/gms :/p; /vendor\/gms-mosey :/p' /build/logs/project-list.txt
# Optional arguments are the exact failed project paths from a completed prior network pass.
if [[ $# -gt 0 ]]; then
  printf 'Retrying only these prior network failures:'; printf ' %q' "$@"; printf '\n'
fi
repo sync -c --no-tags --no-clone-bundle --network-only --jobs="${SYNC_JOBS:-4}" --retry-fetches=2 -- "$@"
repo sync -l --jobs="${CHECKOUT_JOBS:-2}"
for path in vendor/gms vendor/gms-mosey; do
  git -C "$path" lfs pull
  git -C "$path" lfs fsck
 done
python3 - <<'PY'
import zipfile
from pathlib import Path
for p in ('vendor/gms/product/packages/privileged_apps/Phonesky/Phonesky.apk', 'vendor/gms/apex/com.google.android.gmssystem.prodvic.apex'):
    if not zipfile.is_zipfile(p):
        raise SystemExit(f'missing or invalid GMS binary: {p}')
    print(p, Path(p).stat().st_size)
PY
repo manifest -r -o /build/logs/resolved-manifest.xml
if [[ -s /build/resolved-manifest.xml ]]; then
  python3 /build/lock_manifest.py /build/resolved-manifest.xml /build/logs/resolved-manifest.xml
fi
printf '=== sync passed %s ===\n' "$(date -Is)"
