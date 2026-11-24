#!/usr/bin/env bash
# Run from the host; keep all samples and only stop this ROM container.
set -euo pipefail
cd -- "$(dirname -- "$0")"
for f in build.sh stage_dist.sh export_dist.sh; do bash -n "$f"; done
n=enuma-risingos-compile
available_kib() { awk '/^MemAvailable:/ {print $2; exit}' /proc/meminfo; }
[[ $(stat -fc %T /sys/fs/cgroup) == cgroup2fs ]]
[[ $(available_kib) -ge 9961472 ]] || { echo 'Start deferred: host has less than 9.5 GiB available.' >&2; exit 75; }
exec 9>/tmp/enuma-risingos-capped-build.lock
flock -n 9
if docker inspect "$n" >/dev/null 2>&1; then
    [[ $(docker inspect -f '{{.State.Status}}' "$n") == exited ]]
    docker rename "$n" "$n-$(date +%Y%m%d-%H%M%S)"
fi
mkdir -p logs
log="logs/build-capped-$(date +%Y%m%d-%H%M%S).log"
docker create --name "$n" --init --memory=7g --memory-swap=7g --cpus=2 --pids-limit=1024 \
    --mount type=volume,src=enuma-risingos-build-v1,dst=/build \
    enuma-risingos-builder:ubuntu24.04 bash /build/build.sh
id=$(docker inspect -f '{{.Id}}' "$n")
[[ $(docker inspect -f '{{.HostConfig.Memory}} {{.HostConfig.MemorySwap}}' "$id") == '7516192768 7516192768' ]]
tar -cf - --mode=u=rw,go=r --owner=1000 --group=1000 build.sh stage_dist.sh soong-memory-env.patch | docker cp -a - "$id":/build/
docker start "$id" >/dev/null
# Monitor aggregate headroom separately from the cgroup's kernel-enforced limit.
(
    low=0
    while [[ $(docker inspect -f '{{.State.Running}}' "$id" 2>/dev/null) == true ]]; do
        avail=$(available_kib)
        if [[ $avail -lt 2621440 ]]; then
            ((low+=1))
        else
            low=0
        fi
        if ((low >= 2)); then
            printf '%s host memory guard stopped build: available=%s KiB\n' "$(date -Is)" "$avail" | tee -a logs/memory-guard.log
            docker stop -t 5 "$id" >/dev/null
            break
        fi
        sleep 8
    done
) &
watcher=$!
trap 'kill "$watcher" 2>/dev/null || :' EXIT
printf 'Capped build started: %s; log=%s\n' "$n" "$log"
docker logs --follow "$id" >"$log" 2>&1
rc=$(docker wait "$id")
docker inspect -f 'Build state: {{.State.Status}} exit={{.State.ExitCode}} OOMKilled={{.State.OOMKilled}}' "$id"
if [[ $rc != 0 ]]; then exit "$rc"; fi
stage=$(sed -n 's,^Artifacts staged (hardware untested): ,,p' "$log")
[[ -n "$stage" && "$stage" != *$'\n'* ]]
ENUMAROM_BUILD_CONTAINER="$id" bash export_dist.sh "$stage"
