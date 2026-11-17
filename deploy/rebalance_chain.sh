#!/bin/bash
# 链式收尾: 等重排结束 → 补建新品(dry+全量) → 终态复核
cd /home/jason/shopify-admin
L=deploy/rebalance_chain.log
while pgrep -f rebalance_exec.py > /dev/null; do sleep 60; done
echo "== rebalance finished at $(date) ==" >> $L
tail -3 deploy/rebalance.log >> $L
echo "== relaunch dry-run ==" >> $L
env HOME=/home/jason .venv/bin/python deploy/relaunch_new.py >> $L 2>&1
echo "== relaunch full ==" >> $L
env HOME=/home/jason .venv/bin/python deploy/relaunch_new.py 0 >> $L 2>&1
echo "== verify ==" >> $L
env HOME=/home/jason .venv/bin/python deploy/verify_rebalance.py >> $L 2>&1
echo "== CHAIN DONE at $(date) ==" >> $L
