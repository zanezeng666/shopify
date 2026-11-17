#!/bin/bash
# 查定价跑批进度
L=/tmp/pricing_apply.log
echo "== 关键行 =="
grep -E 'round|delist|DONE|ERROR|errors' "$L" | tail -8
echo "--- throttled/429 计数: $(grep -c 'THROTTLED\|429' "$L")"
pgrep -f run_pricing_apply > /dev/null && echo RUNNING || echo EXITED
