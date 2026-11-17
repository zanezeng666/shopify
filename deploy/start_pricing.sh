#!/bin/bash
# 启动定价跑批（完全脱离 ssh 会话）
cd /home/jason/shopify-admin
setsid nohup sudo -u jason .venv/bin/python /tmp/run_pricing_apply.py < /dev/null > /tmp/pricing_apply.log 2>&1 &
sleep 1
pgrep -f run_pricing_apply > /dev/null && echo RUNNING || echo NOT_RUNNING
exit 0
