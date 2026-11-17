#!/bin/bash
# 轮询 pricing_apply.log 直到出现 round1 完成行（或超时 20 分钟）；每分钟报一行防空闲
for i in $(seq 1 20); do
  if grep -q "round1 " /tmp/pricing_apply.log; then
    echo "=== ROUND1 DONE ==="
    grep "round1 " /tmp/pricing_apply.log
    tail -2 /tmp/pricing_apply.log
    exit 0
  fi
  tail -1 /tmp/pricing_apply.log
  sleep 60
done
echo "=== TIMEOUT 20min，最后状态 ==="
tail -1 /tmp/pricing_apply.log
