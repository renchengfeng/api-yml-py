#!/usr/bin/env bash
# 依次执行 conf/ 下所有接口 curl 脚本（{模块}_{分组}_{接口}.sh）。
# 先启动服务：python3 -m lowcode serve -c conf
set -u
for f in "$(dirname "$0")"/conf/*.sh; do
    printf '\n===== %s =====\n' "$(basename "$f")"
    bash "$f"
done
