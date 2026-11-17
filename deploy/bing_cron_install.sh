#!/bin/sh
# 安装 IndexNow 每日增量 crontab（08:30），保留现有任务，幂等可重跑
crontab -l > /tmp/cron_backup_$(date +%Y%m%d) 2>/dev/null
(crontab -l 2>/dev/null | grep -v idxnow_daily; echo "30 8 * * * cd /home/jason/shopify-admin && .venv/bin/python deploy/bing_indexnow_daily.py >> logs/idxnow_daily.log 2>&1") | crontab -
echo "=== 当前 crontab ==="
crontab -l
