# Xiaomi Pad 5 Pro 5G (`enuma`) — RisingOS 续编

这是换机用的构建工程，**不是刷机包**。截至 NAS 停机，源码同步和 `enuma / Google Core / A/B` 预检已通过；Soong 尚未完成编译任务生成，暂无 OTA。二代笔、小窗和日用表现仍需真机验证。历史记录见 [STATUS.md](STATUS.md)，验收设计见 [PROJECT.md](PROJECT.md)。

## 在新电脑从上游重新检出

用 x86-64 Linux 或 WSL2 Ubuntu + Docker。WSL2 将工程和 Docker Linux 虚拟磁盘放在空间充足的 SSD，工程不要放在 `/mnt/c`。按至少 400 GB 可用磁盘准备；16 GB RAM 可以尝试下面的限额构建，但 Soong 在 7 GiB 下可能很慢或退出。推荐 32 GB 起步，64 GB 更稳。不要在 NAS 上运行以下命令，除非明确准备让它恢复工作。

从仓库根目录运行：

```bash
docker build -t enuma-risingos-builder:ubuntu24.04 .
docker volume create enuma-risingos-build-v1
docker run --rm --mount type=volume,src=enuma-risingos-build-v1,dst=/build \
  --user 0 enuma-risingos-builder:ubuntu24.04 chown 1000:1000 /build

m='type=volume,src=enuma-risingos-build-v1,dst=/build'
docker create --name enuma-risingos-sync --init --memory=2g --memory-swap=2g \
  --cpus=2 --mount "$m" -e SYNC_JOBS=2 -e CHECKOUT_JOBS=1 \
  enuma-risingos-builder:ubuntu24.04 bash /build/sync.sh
tar --mode=u=rw,go=r --owner=1000 --group=1000 -cf - \
  sync.sh enuma.xml resolved-manifest.xml lock_manifest.py verify_ota.py verify_enuma_dtbo.py enuma-core.patch \
  | docker cp -a - enuma-risingos-sync:/build/
docker start -a enuma-risingos-sync
test "$(docker inspect -f '{{.State.ExitCode}}' enuma-risingos-sync)" = 0
bash run_capped_build.sh
```

同步以 [enuma.xml](enuma.xml) 加上 [resolved-manifest.xml](resolved-manifest.xml) 固定 1,267 个项目；下载与检出都成功、GMS LFS 校验通过后，才写出通过记录。若上游移动引用或网络中断，检查 `docker logs enuma-risingos-sync`，修复后可 `docker start -a enuma-risingos-sync` 复用已下载数据，别删卷。启动编译脚本要求 Linux 主机可用内存至少 9.5 GiB，容器为 7 GiB 硬上限且不使用 swap；若 WSL2 报低于门槛，不要移除保护。构建成功并通过静态校验后才导出到 `dist/`，标记 `UNTESTED`。

## 保留 NAS 上已下载的缓存

此仓库只保存工程、版本和验收文件，不存放数百 GB 的 Android 工作树、`.repo` 对象、Google/小米二进制、私钥、构建缓存或回退镜像。若要免重下载，另走局域网或外置 SSD 迁移容器卷；让两边构建先处于停止状态。专用卷 `enuma-risingos-build-v1` 中，至少需要 `src/`（**包含隐藏目录 `src/.repo`**）、`bin/`、`logs/resolved-manifest.xml` 和 `/build` 根目录的工程脚本。以同一个 `/build` 挂载路径恢复，保留软链接、硬链接和数值 UID/GID 1000；普通 Windows 文件复制会丢失其中部分信息。`src/out/` 和 `ccache/` 可另行保留，但不是源码。刷新新工程的校验脚本和补丁后才能继续。下面的迁移是可选步骤，NAS 未执行。应先在目标 SSD 建好空卷，传输期间不要同时编译，避免在 NAS 上生成第二份大归档：

```bash
# 在新电脑的 Linux 终端运行；替换 NAS_SSH_HOST 和 SSH_USER
set -o pipefail
ssh SSH_USER@NAS_SSH_HOST 'docker run --rm --network none --cpus=1 --mount type=volume,src=enuma-risingos-build-v1,dst=/build,readonly enuma-risingos-builder:ubuntu24.04 tar -C /build --numeric-owner --exclude=src/out -cf - src bin/repo logs/resolved-manifest.xml' \
  | docker run --rm -i --network none --user 0 --mount type=volume,src=enuma-risingos-build-v1,dst=/build enuma-risingos-builder:ubuntu24.04 tar -C /build --numeric-owner -xpf -

# 导入成功后，用本仓库的校验器与补丁，不需重新同步
m='type=volume,src=enuma-risingos-build-v1,dst=/build'
docker create --name enuma-import-scripts --mount "$m" \
  enuma-risingos-builder:ubuntu24.04 true
tar --mode=u=rw,go=r --owner=1000 --group=1000 -cf - \
  enuma-core.patch verify_ota.py verify_enuma_dtbo.py \
  | docker cp -a - enuma-import-scripts:/build/
docker rm enuma-import-scripts
bash run_capped_build.sh
```

NAS 侧 SSH 用户须已能执行 Docker；如果用 SMB 挂载传文件，传 tar 网络流或单个归档文件，不要逐个拷贝源码目录。

## 发布到自己的 GitHub 私有仓库

在自己的终端，[安装 GitHub CLI](https://cli.github.com/)，用浏览器完成 `gh auth login --hostname github.com --web`。解压后进入含本文件的目录，运行：

```bash
git init -b main
git add -- .
git diff --cached --stat
git commit -m 'Add enuma RisingOS build handoff'
gh repo create enuma-risingos-build --private --source=. --remote=origin --push
```

Git 如果提示作者身份未配置，设置你自己的 Git 姓名及 [GitHub noreply 邮箱](https://github.com/settings/emails)后再提交。不要把密码、令牌或签名私钥写入这些文件。
