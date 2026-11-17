#!/bin/bash
cd /home/jason/shopify-admin
sudo -u jason env HOME=/home/jason nohup .venv/bin/python deploy/backfill_stock.py > /tmp/backfill.log 2>&1 < /dev/null &
sleep 5
echo "--- log ---"
tail -2 /tmp/backfill.log
ps -ef | grep backfill_stock | grep -v grep | awk '{print $2, $1}'
