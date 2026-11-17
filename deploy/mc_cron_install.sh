#!/bin/sh
# MC 每周一体检：违规明细拉取 + 与基线对比（防复发监控）
CRON_LINE="30 7 * * 1 cd /home/jason/shopify-admin && .venv/bin/python deploy/mc_issues_pull.py >> logs/mc_weekly_check.log 2>&1"
(crontab -l 2>/dev/null | grep -v mc_issues_pull; echo "$CRON_LINE") | crontab -
crontab -l | tail -n 4
