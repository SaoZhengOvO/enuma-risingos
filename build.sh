#!/usr/bin/env bash
set -eo pipefail
umask 022
cd /build/src
mkdir -p /build/logs /build/dist
exec > >(tee -a /build/logs/build.log) 2>&1
printf '\n=== build start %s ===\n' "$(date -Is)"
read -r memory_max </sys/fs/cgroup/memory.max
read -r swap_max </sys/fs/cgroup/memory.swap.max
if [[ ! $memory_max =~ ^[0-9]+$ || $memory_max -gt 7516192768 || $swap_max != 0 ]]; then
    echo 'ROM build requires a Docker memory limit of at most 7 GiB and zero container swap.' >&2
    exit 64
fi
[[ ${BUILD_JOBS:-1} == 1 ]]
export BUILD_JOBS=1 GOGC=30 GOMEMLIMIT=5GiB GOMAXPROCS=2
printf 'Resource limits: memory=%s swap=%s GOGC=%s GOMEMLIMIT=%s GOMAXPROCS=%s\n' \
    "$memory_max" "$swap_max" "$GOGC" "$GOMEMLIMIT" "$GOMAXPROCS"
[[ -s /build/logs/resolved-manifest.xml ]]
[[ $(git -C build/soong rev-parse HEAD) == 8133292f208ee23a7211f45be38e298f7f39981f ]]
if ! git -C build/soong apply --check --reverse /build/soong-memory-env.patch 2>/dev/null; then
    git -C build/soong apply --check /build/soong-memory-env.patch
    git -C build/soong apply /build/soong-memory-env.patch
fi
git -C build/soong diff --check HEAD
[[ $(git -C device/xiaomi/enuma rev-parse HEAD) == 555d8599888b185f83b176c1bdc4ec1cdaf79913 ]]
[[ $(git -C kernel/xiaomi/sm8250 rev-parse HEAD) == 6b34d24765327d746074c8e53b5ad0d24a51acc7 ]]
git -C device/xiaomi/enuma diff --quiet HEAD -- BoardConfig.mk board-info.txt device.mk stylus-bridge
if git -C device/xiaomi/enuma apply --check --reverse /build/enuma-core.patch 2>/dev/null; then
    printf 'Google Core device patch already applied\n'
else
    git -C device/xiaomi/enuma apply --check /build/enuma-core.patch
    git -C device/xiaomi/enuma apply /build/enuma-core.patch
fi
git -C device/xiaomi/enuma diff --check HEAD
awk 'END { if (NR != 1 || $0 != "require board=enuma") exit 1; }' <(sed -n '/^require board=/p' device/xiaomi/enuma/board-info.txt)
grep -Eq '^TARGET_OTA_ASSERT_DEVICE[[:space:]]*:=[[:space:]]*enuma[[:space:]]*$' device/xiaomi/enuma/BoardConfig.mk
grep -q 'stylus_use_old_driver, true' device/xiaomi/enuma/device.mk
grep -q 'stylus-bridge' device/xiaomi/enuma/device.mk
grep -q 'CONFIG_MACH_XIAOMI_ENUMA=y' kernel/xiaomi/sm8250/arch/arm64/configs/vendor/xiaomi/enuma.config
grep -q 'LMOFreeformSidebar' vendor/rising/config/packages.mk
grep -q 'android.software.freeform_window_management.xml' vendor/rising/config/rising.mk
# Soong fsgen validates generated DTBO paths as source-relative paths.
export OUT_DIR=out USE_CCACHE=1 CCACHE_EXEC=/usr/bin/ccache CCACHE_DIR=/build/ccache
# Keep the verified bundled executor; preserve earlier absolute-dir outputs separately.
export SOONG_NINJA=ninja
ccache --max-size=30G
source build/envsetup.sh
source vendor/lineage/vars/aosp_target_release
[[ -n "$aosp_target_release" ]]
lunch "lineage_enuma-${aosp_target_release}-userdebug"
[[ $(get_build_var TARGET_DEVICE) == enuma ]]
[[ $(get_build_var RISING_PACKAGE_TYPE) == CORE ]]
[[ $(get_build_var AB_OTA_UPDATER) == true ]]
printf 'Preflight passed: enuma/CORE/A-B, build jobs=%s\n' "${BUILD_JOBS:-2}"
if [[ ${1:-} == --preflight ]]; then exit 0; fi
# Use the ROM target rather than stitching partition images from other builds.
# Call the actual build entry point so shell wrappers cannot mask a failed build.
if build/soong/soong_ui.bash --build-mode --all-modules --dir="$PWD" \
    -j"${BUILD_JOBS:-2}" bacon target-files-package; then
    :
else
    rc=$?
    printf 'ROM build failed (Soong exit %s); staging skipped.\n' "$rc" >&2
    exit "$rc"
fi
printf '=== build targets passed %s ===\n' "$(date -Is)"
export ENUMAROM_OTA_CERT="$(get_build_var DEFAULT_SYSTEM_DEV_CERTIFICATE).x509.pem"
bash /build/stage_dist.sh
