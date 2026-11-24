# enuma · RisingOS Revived Google Core 构建工程

这是构建工程，不是刷机包。目标为 Xiaomi Pad 5 Pro 5G（`enuma`、M2105K81C、Bootloader 已解锁）；不发布 `elish` 包。5G 非验收项，也不以修改基带换取启动。

## 选型

- RisingOS Revived `seventeen` / Android 17，manifest 固定为 `ecb587a4b0d36e65a3eb795c9b92cbbafa58ccce`。Android 16 QPR2 清单的非公开 GMS Git 端点返回 401，因此未选。
- [设备与依赖清单](enuma.xml) 固定 `enuma`、平板共用层、内核和 vendor 提交。[Google Core 补丁](enuma-core.patch) 只调整产品 GMS 选项，不碰 `enuma` OTA 断言、触屏、指纹、蓝牙和手写笔设备代码。Core 版包括 Play 商店和 Google Play 服务，并尽量避免预装不需要的 Google 应用。
- 小窗沿用 RisingOS 的 `LMOFreeform`、`LMOFreeformSidebar` 和自由窗口能力。固定源码已确认[系统服务接线](https://github.com/RisingOS-Revived/android_frameworks_base-new/blob/ccf6752800f4e0cd27d5427b863c1440e435b823/services/freeform/java/com/android/server/display/FreeformService.java#L38-L57)以及[侧栏默认关闭](https://github.com/RisingOS-Revived/android_packages_apps_LMOFreeform/blob/406622111070c39d1f193be75876972246bee6f9/sidebar/app/src/main/java/com/libremobileos/sidebar/receiver/BootReceiver.kt#L22-L32)。首次使用需在侧栏设置中启用并添加应用。交互接近澎湃侧栏，但不是小米澎湃组件；保留 RisingOS 自定义面板，不替换桌面。
- 手写笔保留三层：`enuma` [设备树的 NovaTek 笔节点](https://github.com/LineageOS/android_kernel_xiaomi_sm8250/blob/6b34d24765327d746074c8e53b5ad0d24a51acc7/arch/arm64/boot/dts/vendor/qcom/enuma-sm8250.dtsi#L292-L305)启用 `novatek,pen-support`；[内核驱动](https://github.com/LineageOS/android_kernel_xiaomi_sm8250/blob/6b34d24765327d746074c8e53b5ad0d24a51acc7/drivers/input/touchscreen/nt36523/nt36xxx.c#L1915-L1954)解码笔尖数据并上报 `ABS_PRESSURE`；MiPadParts 管理笔，[`stylus-bridge`](https://github.com/awkox/android_device_xiaomi_enuma/blob/555d8599888b185f83b176c1bdc4ec1cdaf79913/stylus-bridge/main.c)映射 BLE 按键，按键产生的 0/255 事件不是笔尖压感。这些是源码证据，仍待编译产物和二代笔真机实测。

## 构建与验收

1. [Dockerfile](Dockerfile) 构建隔离 Ubuntu；源码和产物写入 `enuma-risingos-build-v1` 单项目 Docker 卷，非 root Git 写入已验证。
2. `enuma-risingos-sync` 运行 [sync.sh](sync.sh)。Repo 已成功初始化并校验 manifest 提交，清单包含 1,267 个项目。预检已实际下载 [Google Play 商店和 Play 服务的 LFS 对象](logs/gms-probe-checkout.log)，两者 SHA‑256 与固定 Git 提交一致。另在[断网容器](logs/gms-offline-hydration.log)用同一固定提交和主缓存还原 APK/APEX，SHA‑256 与 `git lfs fsck` 均通过；主工作树未被修改。主源码同步仍在进行，全部依赖须经检出及 LFS 实体校验。[宿主同步日志](logs/sync-container.log)。
3. 同步成功后，`enuma-risingos-compile` 运行 [build.sh](build.sh)，先验 `enuma/CORE/A-B`，然后 `m bacon target-files-package`。
4. [stage_dist.sh](stage_dist.sh) 与 [verify_ota.py](verify_ota.py) 检查 OTA 只接受 `enuma`、A/B 完整包元数据、payload 哈希和签名证书，逐个核对引导镜像和目标文件及 OTA 的分区摘要，并检查 Google Play、侧栏、小窗和笔桥接进入产物。元数据哈希按[固定版本的 update_engine](https://github.com/Evolution-X/system_update_engine/blob/1ef2cbc4f6f3fee374b9124b005da6eab13f8880/payload_generator/payload_properties.cc#L92-L105)计算：只包含头和清单，整包哈希仍覆盖紧随其后的签名块。修正后签名模拟包通过，错配 `dtbo`、错机型、重复分区、增量 payload、越界签名块及错误哈希范围均被识别。另用[设备树检查脚本](verify_enuma_dtbo.py)核验 `dtbo.img` 中实际存在 `enuma`（`qcom,board-id = <46 0>`）和已启用的 NovaTek 笔节点。同机型已发布的 [LineageOS DTBO](https://github.com/davydes/device_xiaomi_enuma/releases/tag/LOS24.0_20261116) 经 SHA‑256 校验后，用作正例；错机型、缺笔节点及截断镜像会被拦截。该镜像不用于 RisingOS 构建或刷机。实际 RisingOS OTA 尚无验证结果。
   [独立编译日志](logs/compiled-dtbo-smoke.log)：用固定内核直接编出的 `enuma` 覆盖树通过检查，实际编出的 `elish` 覆盖树被拦截。`libfdt` 将 `enuma` 覆盖树分别合入 `kona`、`kona-v2`、`kona-v2.1` 底树，三者均保留已启用的 `/soc/spi@990000/novatek@0` 笔节点。该冒烟产物不刷机，也不验证硬件。另用已检出的 Clang 12 按 RisingOS 顺序合并四份内核配置；[Kconfig 预检](logs/kernel-kconfig-clang12-smoke.log)确认最终 `.config` 启用 `CONFIG_MACH_XIAOMI_ENUMA` 与 `CONFIG_TOUCHSCREEN_NT36523_HOSTDL_SPI`。进一步将 NovaTek 的 `nt36xxx.o` [编成 AArch64 ThinLTO 位码](logs/kernel-stylus-object-clang12-smoke.log)，并在真实中断处理函数中找到 `EV_ABS/ABS_PRESSURE` 的可变值调用。正式 Clang `r584948` 检出后，已切换到 [Clang 22 与 AOSP sysroot 重编](logs/kernel-stylus-clang22-smoke.log)，最终驱动的两份 ThinLTO 模块均为 AArch64，主回调仍以可变值报告 `ABS_PRESSURE`。这些只验证配置和驱动编译，未替代完整内核、OTA 或真机测试。
   实际 payload 的分区名须与[固定设备配置的 10 个 A/B 分区](https://github.com/web1n/android_device_xiaomi_sm8250-common/blob/3c71874002bd93b1c883c946064d5153fc9d7f69/BoardConfigCommon.mk#L14-L24)一致，不包含 `modem`、`xbl` 等底层固件分区，也不接受旧式 `updater-script`。已使用签名模拟包验证允许和拦截分支；这不代表射频功能通过。
5. 编译容器成功退出后，把日志输出的 `/build/dist/RisingOS-…-UNTESTED` 传给 `bash export_dist.sh <暂存路径>`（[脚本](export_dist.sh)）。它在工作区重新核对 SHA‑256，通过后才发布。模拟测试覆盖正常导出、同名目标、镜像篡改和构建未退出四种情况。
6. 开发密钥或签名来源待确认的产物只作为构建候选，不当成日用发布。刷机前先核对本次 ROM 的镜像、签名与回退底包；`vendor_boot` 包含 Recovery 资源，不混刷其他 ROM 的镜像。候选原厂回退版本：小米 CDN 的 [enuma 中国版 OS1.0.3.0.TKZCNXM Fastboot 包](https://cdnorg.d.miui.com/OS1.0.3.0.TKZCNXM/enuma_images_OS1.0.3.0.TKZCNXM_20240508.0000.00_13.0_cn_fc06cc99cc.tgz)。已实测首 4 KiB 可下载，响应总长度 5,411,798,301 字节；[索引发布的 MD5](https://miuidownloader.com/hyperos/enuma/stable/os1-0-3-0-tkzcnxm) 为 `fc06cc99cc67649c61917638667ae67c`。完整包与实际回退尚未验证。

## 真机验收

- 正常开机／Recovery、重启与原厂回退；Wi‑Fi、蓝牙、音频、相机、充电、待机唤醒与横竖屏。首启后可运行 [`python3 check_first_boot.py`](check_first_boot.py)（需 ADB 和已启用 USB 调试），只读核对 `enuma`、Google Core、Play、小窗与笔设置组件；脚本已通过模拟 ADB 正例及五类反例，尚未接入真机。
- Google 登录、Play 安装更新；RisingOS 自定义面板保存及重启后状态。
- 官方白色二代笔配对、磁吸后重连，分别检查书写、压感、掌触、按键和横竖屏坐标。压感用支持压力的绘图应用，在不按笔键时轻重连续运笔；如有调试权限，用 `adb shell getevent -lp` 定位 NovaTek 笔的输入节点，再用 `adb shell getevent -lt /dev/input/eventN` 观察 `ABS_PRESSURE` 的多个级别。单次按键导致的 0/255 变化不算通过。
- 首次启用侧栏并添加两个常用应用，再验证侧栏唤出、开小窗、拖拽、缩放、最小化、还原、关闭和旋屏；重启后检查侧栏设置是否保留，连续切换时观察掉帧和发热。

没有接入目标真机，任何静态证据均不等于已通过以上测试。
