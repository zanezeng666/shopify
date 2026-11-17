#!/bin/bash
# 安装 abandoned_watch 每日 09:00 crontab（幂等：已存在则跳过）
CRON_LINE="0 9 * * * cd /home/jason/shopify-admin && .venv/bin/python deploy/abandoned_watch.py >> /home/jason/shopify-admin/deploy/abandoned_cron.log 2>&1"
CURRENT=$(crontab -l 2>/dev/null)
if echo "$CURRENT" | grep -q "abandoned_watch.py"; then
    echo "SKIP: abandoned_watch cron 已存在"
else
    (echo "$CURRENT"; echo "$CRON_LINE") | crontab -
    echo "INSTALLED: abandoned_watch cron"
fi
crontab -l | tail -n 5
