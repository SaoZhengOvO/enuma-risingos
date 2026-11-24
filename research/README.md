# Xiaomi Pad 5 Pro 5G (`enuma`) → RisingOS Revived：调研与开工清单

日期：2026-11-23。调研范围：GitHub 可公开发现的 Android ROM、设备树、内核/vendor、Recovery、固件和同平台参照。未做完整源码同步、编译或刷机。

## 首选路线

以 `enuma` 为唯一首版刷机目标。优先比对 RisingOS Revived 的 [`sixteen-qpr2`](https://github.com/RisingOS-Revived/android/tree/sixteen-qpr2)（manifest 默认以 LineageOS `lineage-23.2` 为基线）和 [davydes 的 `enuma` 23.2 设备树](https://github.com/davydes/device_xiaomi_enuma/tree/lineage-23.2)。[`seventeen`](https://github.com/RisingOS-Revived/android/tree/seventeen) / LineageOS 24.0 是备选；已有 Android 17 的 `enuma` 设备树和现成 LineageOS 供验证。构建前检查 manifest 全部远端、设备树与 common/kernel/vendor/硬件接口版本；本轮仅核验重点仓库和文件可访问，不等于 `repo sync` 可完整通过。

- `enuma` 树里的 `board-info.txt` 有 `require board=enuma`，`BoardConfig.mk` 有 `TARGET_OTA_ASSERT_DEVICE := enuma`，并单独指定内核配置和单 SIM vendor 属性。某些双机型包的存在不代表任意包都能互刷，也不代表差异只有 5G；保留机型检查，不混刷 Wi‑Fi 版的底层固件、vendor/odm 或整套分区镜像。
- [手写笔桥接源码](https://github.com/davydes/device_xiaomi_enuma/blob/lineage-23.2/stylus-bridge/main.c) 可复用：将小米笔蓝牙按键转成输入事件；设备树也有 `PadParts` 手写笔设置。桥接源码里的 `ABS_PRESSURE` 不等同于笔尖实际压感测试。配对、书写、真实压感、防误触、快捷键和重连分别验收。
- RisingOS Android 16 QPR2 有 [Freeform WindowManager Shell](https://github.com/RisingOS-Revived/frameworks_base/blob/sixteen-qpr2/libs/WindowManager/Shell/src/com/android/wm/shell/freeform/FreeformTaskTransitionHandler.java) 源码；不等于 `enuma` 已有小窗入口。首版验收：常用应用能从可见入口开启小窗，可拖拽、缩放、关闭；横竖屏切换后仍可操作。类澎湃小窗样式与自由窗口底层能力分别确认。

## 资源索引

| 类别 | 来源 | 用途 |
| --- | --- | --- |
| `enuma` Android 15–17 设备树 | [xiaomi-enuma-dev 多分支](https://github.com/xiaomi-enuma-dev/android_device_xiaomi_elish_enuma/branches)、[davydes](https://github.com/davydes/device_xiaomi_enuma/branches)、[awkox Android 17](https://github.com/awkox/android_device_xiaomi_enuma)、[xiliahz](https://github.com/xiliahz/device_xiaomi_enuma)、[YiQiuYes](https://github.com/YiQiuYes/android_device_xiaomi_enuma) | 首选 davydes，对照不同版本输入、启动和无线配置 |
| `elish` 设备树/ROM | [web1n Android 16/17 设备树](https://github.com/web1n/android_device_xiaomi_elish/branches)、[LineageOS 23.2 主题](https://xdaforums.com/t/rom-unofficial-a16-elish-lineageos-23-2-for-xiaomi-pad-5-pro-wifi.4764518/)、[LineageOS 24 主题](https://xdaforums.com/t/rom-unofficial-a17-elish-lineageos-24-for-xiaomi-pad-5-pro-wifi.4804913/)、[xiliahz 的 Lunaris/Infinity-X](https://github.com/xiliahz/device_xiaomi_elish/releases)、[Rinko-Studio ArrowOS](https://github.com/Rinko-Studio/android_device_xiaomi_elish) | 对照手写笔、显示和共用硬件；不当作 enuma 刷机包 |
| SM8250 公共层 | [LineageOS common](https://github.com/LineageOS/android_device_xiaomi_sm8250-common/branches)、[web1n common](https://github.com/web1n/android_device_xiaomi_sm8250-common/branches)、[LineageOS kernel](https://github.com/LineageOS/android_kernel_xiaomi_sm8250/branches)、[Xiaomi 移植内核](https://github.com/xiaomi-enuma-dev/kernel_xiaomi_sm8250)、[MiCode `elish-r-oss`](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/tree/elish-r-oss) | 需与产品分支、内核配置和 proprietary blobs 严格配对；不是互刷依据 |
| proprietary vendor 候选 | [`enuma` 23.2 vendor](https://github.com/1582130940/android_vendor_xiaomi_enuma/tree/lineage-23.2)、[`enuma` Android 15 vendor](https://github.com/xiaomi-enuma-dev/android_vendor_xiaomi_enuma)、[`enuma` Android 17 vendor](https://github.com/awkox/android_vendor_xiaomi_enuma)、[`elish` vendor](https://github.com/web1n/proprietary_vendor_xiaomi_elish) | 公开仓库已找到，提取来源、版本及配套固件待复核后再定；优先用 enuma 同机型源 |
| `enuma` 对照包 | [davydes LineageOS 24.0](https://github.com/davydes/device_xiaomi_enuma/releases/tag/LOS24.0_20261116)、[leodroid99 LineageOS 23.2 beta](https://github.com/leodroid99/LineageOS-23.2-enuma/releases/tag/v23.2-enuma-beta1)、[xiliahz Lunaris / AxionOS](https://github.com/xiliahz/device_xiaomi_enuma/releases) | 都不是 RisingOS；23.2 beta 作者报告真机启动和单一运营商 LTE，未证实用户当地 5G |
| 双机型社区例子 | [uwuAOSP `elish/enuma`](https://github.com/Liangzaigrape/uwuAOSP-elish-enuma) | 辅助考察平板产品化和手写笔设置，非 RisingOS，也不是通用互刷证明 |
| RisingOS 平板参照 | [`pipa` 设备树](https://github.com/RisingOS-Revived-Devices/android_device_xiaomi_pipa)、[RisingOS 官方 `pipa` 安装文档](https://github.com/RisingOS-Revived/official_devices/blob/fifteen/OTA/guide/pipa.md) | 同 Snapdragon 870 的小米平板 6；只参考产品配置和可用功能，不混用其包或镜像 |
| 底包/救援参考 | [enuma HyperOS/MIUI 下载索引](https://mifw.net/devices/enuma)、[Xiaomi Firmware Updater](https://xmfirmwareupdater.com/firmware/enuma/)、[enuma TWRP 设备树](https://github.com/zhxt/android_device_xiaomi_enuma-twrp)、[elish OrangeFox 设备树](https://github.com/ymdzq/OFRP-device_xiaomi_elish) | 用完整系统版本号匹配机型原厂包及还原方式；Recovery 仓库是候选，不代表适用新 ROM |

未发现可直接采用、发布者明确标注支持 `enuma` 的 RisingOS 成品，也未找到可直接作为本机成品的 `elish` RisingOS 发布。通用 GSI 不作为首选，因为笔、相机、休眠等需求依赖设备专用适配。

## 本轮缓存与校验

[仓库/分支/提交清单](upstream/SOURCES.tsv)、[SHA-256](upstream/SHA256SUMS)。十份源码快照按提交固定并已校验。另存公开发布元数据：[LineageOS 23.2 beta](upstream/enuma-lineage-23.2-beta1-release.json)、[LineageOS 24.0](upstream/enuma-davydes-lineage-24.0-release.json)、[Lunaris](upstream/enuma-lunaris-release.json)。没有下载或执行第三方刷机脚本，没有下载上述 ROM 镜像及完整 AOSP 源码。

## 下一轮输入与验收

1. 当前系统完整版本号（HyperOS/MIUI 版本，例如 `OSx.x.x.x.TKZCNXM`），Bootloader 是否已解锁，当前是否为第三方 ROM/Recovery。截图可打码序列号、IMEI；无需账号或密钥。如果当前在第三方 ROM，请补上一次官方底包版本，找不到就写未知。
2. 手写笔代数/品牌型号；目前能否在这台平板上写字、压感和按键是否正常。
3. SIM 的要求：必须保留 5G / 有 LTE 即可 / 纯 Wi‑Fi 可接受；如果必须保留，提供运营商名称，不要号码。
4. 是否需要 Google Play（默认先编 Vanilla，便于排除变量）；小窗是否必须像澎湃 OS，还是可缩放、可拖动的浮窗就行。
5. 若手头有 Linux 编译机，只发 CPU、RAM、可用磁盘容量和发行版，勿发登录凭据。当前工作主机是 Linux x86_64、4 核、约 15 GiB RAM、约 875 GiB 工作盘空闲；`repo`、`git-lfs`、Java 未在 `PATH`。可先在此准备适配工程，全量编译优先用资源更充裕的机器：[AOSP 构建要求](https://source.android.com/docs/setup/start/requirements)。

首版真机验收：开机/Recovery 与原厂回退、120 Hz 及横竖屏、日常切换流畅度、手写笔各项、小窗/自定义设置、触屏、Wi‑Fi/蓝牙、音频/麦克风、相机、充电、待机唤醒；按要求额外验 SIM、LTE/5G。未上目标真机前，产物只标为测试包，不作为日用稳定版发送。