# 构建检查点 · 2026-11-24 10:12（UTC+8）

**按用户要求停止 NAS 编译。** 限额构建任务 `bash-67ff7c61e5aa4b3b` 和容器已退出 143，非 OOM；回退包容器仍暂停，持久目标仍为 `paused` / `disarmed`。主机可用内存回到 10.82 GiB，命名卷保留。暂无 OTA；下面是停止前的记录。

**用户要求限内存续编。** [限额启动脚本](run_capped_build.sh)已复用已同步源码和相对输出目录，启动任务 `bash-67ff7c61e5aa4b3b`（[构建日志](logs/build-capped-20261124-093032.log)）；容器实测 `memory.max=7516192768`、`memory.swap.max=0`，Soong 产品预检已通过，单编译任务、容器 CPU 上限 2 核。连续两次采样主机 `MemAvailable` 低于 2.5 GiB 则停止本构建；实际 `soong_build` 环境已读回 `GOGC=30`、`GOMEMLIMIT=5GiB`、`GOMAXPROCS=2`；当时容器占约 2.36 GiB，主机约 8.5 GiB 可用，容器无 OOM 事件。构建通过才自动校验和导出，现无 OTA。回退包继续暂停避免并发读写。宿主目标工具拒绝由模型重启用户暂停的目标，但本次直接请求启动的独立构建任务已运行。

**此前用户打断时的停机记录。** 持久目标 rev 3 为 `paused` / `disarmed`；编译容器收到停止信号退出 143（非 OOM），回退包容器已暂停，完整 5,411,798,301 字节候选仍在 `.assembling` 且未通过校验。停止前 Soong RSS 约 9.9 GiB，主机可用约 0.65 GiB；停止后可用约 10 GiB。Docker 根目录原为并仍为 `/vol1/docker`，底层 `/vol1` 实测余 711 GiB、使用率 62%。不自动重开、不迁移 Docker、不删除源码或文件。下面的运行状态是暂停前记录。

**当前状态：源码完整，第三轮整包构建运行中，暂无 OTA。** Siso 首轮无法加载 `@config//main.star`；第二轮使用 AOSP Ninja，通过了执行器初始化，Soong 在 `soong_filesystem_creator` 中拒绝绝对路径的 DTBO。第三轮使用源码根目录下的相对 `OUT_DIR=out`，旧 `/build/out` 保留。已通过 `enuma/CORE/A-B` 产品预检；完整任务图待生成。运行任务 `bash-05d5b65323144e4a`，容器 `enuma-risingos-compile`，[本轮构建日志](logs/build-relative-container.log)。

**原厂回退包：**此前整文件超时，分段任务保留 155 段、共 5,176,917,277 字节。对一个真实缺段实测 `curl` 接收正确 HTTP 206、`Content-Range` 和 32 MiB；当前只补缺失的七块（任务 `bash-25d7f3fea09b4cf2`，[进度日志](logs/stock-rollback-curl.log)）。七块已全部补齐，总字节数达到 5,411,798,301；完整归档仍须通过 MD5、SHA‑256 及内容检查。

**08:23 资源排查：**主机 3 GiB swap 已满，Soong RSS 约 9.8 GiB。短时暂停本项目回退包容器，主机 I/O full PSI 60 秒窗口仅从 75.17% 降至 74.53%，未见明显缓解；Soong CPU 计数仍增加，回退容器已恢复运行。未重启构建，未调整主机级配置。以下是早期检查记录。

目标：制作仅限 `enuma` 的 RisingOS Revived Android 17 Google Core ROM；保留设备和固件身份、官方白色二代笔适配，以及 RisingOS 的侧栏小窗。用户要求 5G 可选，不混用 `elish` 镜像，完成后再通知。Bootloader 已解锁，暂无连接的 `enuma` 真机可用。

- Docker 镜像 `enuma-risingos-builder:ubuntu24.04`，命名卷 `enuma-risingos-build-v1`。非 root Git 初始化、Java 21、Git LFS 3.4.1 已通过。Repo 从 GitHub 镜像启动，实际检出 RisingOS manifest `ecb587a4b0d36e65a3eb795c9b92cbbafa58ccce`；有效项目清单 1,267 条。
- 首次网络同步 `enuma-risingos-sync` 因 `art`、`build/soong`、`cts`、`dalvik` 的 DNS 错误退出 1。复用同卷的 `enuma-risingos-sync-retry` 对这四项补抓已退出成功（目标引用短哈希依次 `778d1aee98`、`8133292f2`、`06b5eeba0e5`、`9d9131f9`）；不重下成功项目。02:20 全量检出与两个 Google 项目的 `git lfs fsck` 通过，同步容器退出 0。`/build/logs/resolved-manifest.xml` 310,585 字节已生成，任务 `bash-964fbacaef2c4d02` 随后已启动 `enuma-risingos-compile`；目前是整包构建的环境与产品配置阶段，还没有 OTA。详见 [首次同步日志](logs/sync-container.log) 和 [增量恢复日志](logs/sync-retry-container.log)。
- 固定 GMS 提交 `619534d5a9880377697935d1978d871ec1af71b7` 的 Play 商店及 GMS Core 已实际下载、SHA‑256 和内部条目均通过；七个 GMS LFS 对象随后全部预取或复用，`git lfs fsck` 与主源码对象目录的逐个 SHA‑256 已通过。主工作树中的 Play Store APK 103,896,900 字节及 GMS Core APEX 146,546,688 字节均通过 ZIP 容器检查。[隔离断网还原](logs/gms-offline-hydration.log)也通过两份实体的 SHA‑256 和 `git lfs fsck`。见 [Play 组件预检](logs/gms-probe-checkout.log) 和 [全部 GMS 缓存日志](logs/gms-cache-prefetch.log)。
- 原厂 `enuma` Fastboot 回退包从小米 CDN 限速下载中，任务 `bash-410b2cc6972b4c50`，容器 `enuma-stock-rollback`，目标 `/build/rollback`；验收为 5,411,798,301 字节、媒体索引的 MD5 `fc06cc99cc67649c61917638667ae67c`、归档目录以及本地归档 SHA‑256。原厂包和自编 ROM 产物分开。
- 02:09 时已为 1,174 / 1,267 个项目写出实际 Git 工作树索引，原厂回退包已下载 4,454,219,776 / 5,411,798,301 字节。设备和内核 4.19.325 `6b34d24765327d746074c8e53b5ad0d24a51acc7` 已检出；正式主机 Clang 22 `r584948` 可执行，[设备驱动单独编译](logs/kernel-stylus-clang22-smoke.log)通过，并在 ARM64 ThinLTO 产物中证实 NovaTek 回调报告可变 `ABS_PRESSURE`。仍在检出其他依赖（按 `.git/index` 检查；`repo list` 的 1,267 条仅代表清单），整包编译尚未开始。另在禁用 Git 传输协议的预检中，设备、内核、vendor 及 RisingOS 的 9 个固定提交对象均已在本地缓存；提交存在不代表文件已检出。
- 已准备 [编译脚本](build.sh)、[分发打包](stage_dist.sh)、[OTA 校验脚本](verify_ota.py) 和 [工作区导出脚本](export_dist.sh)。Docker 停止容器复制实测通过。导出脚本适配继承 ACL，在模拟测试中通过文件哈希验证、拒绝损坏镜像/重名路径/运行中的构建。正式验收顺序：完整同步 → 目标配置核验 → 编译 → 签名、`pre-device=enuma`、payload、引导镜像、GMS/笔/小窗检查 → 输出到 `/build/dist` 并导出；模拟样本不是实际 OTA 证据。00:39 对照固定 revision `1ef2cbc4f6f3fee374b9124b005da6eab13f8880` 的 OTA 生成器，修正 `METADATA_SIZE` 与 `METADATA_HASH` 不计签名块、`FILE_HASH` 仍计入的边界；正例及 8 个反例已通过并复核构建卷中的脚本 SHA‑256。01:08 部署 [DTBO 设备树核验](verify_enuma_dtbo.py)：已发布的同机型 LineageOS DTBO 哈希匹配后实测识别 `enuma` board 46 与启用的 NovaTek 笔节点，缺节点、错机型、截断被拦截；该第三方镜像只作样本，未用于构建。真实开机、二代笔压感和小窗体验仍须在真机验证。

出现失败先收集上述任务结果、Docker 退出码和持久日志，再针对单个失败原因处理。同个卷中不要并行启动两份 Repo 同步或两份编译。已有源码与构建输出保留，勿从零重来。新版 [同步脚本](sync.sh) 中 `repo list -a` 补齐了网络同步前的项目列表；运行中的脚本不覆盖，容器列表已单独补齐。
