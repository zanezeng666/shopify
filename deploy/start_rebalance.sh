#!/bin/bash
# 全店重排执行（新规则：三类全DRAFT + 死库存下架 + 误伤恢复）
cd /home/jason/shopify-admin
setsid nohup env HOME=/home/jason .venv/bin/python deploy/rebalance_exec.py --go \
  > deploy/rebalance_go.log 2>&1 < /dev/null &
echo "started pid=$!"
