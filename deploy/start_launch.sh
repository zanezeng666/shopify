#!/bin/bash
# 全量建品启动器（以 jason 后台运行，脱离会话）
cd /home/jason/shopify-admin
sudo -u jason env HOME=/home/jason nohup .venv/bin/python deploy/launch_new.py 0 > /tmp/launch.log 2>&1 < /dev/null &
sleep 5
echo "--- log head ---"
tail -3 /tmp/launch.log
echo "--- proc ---"
ps -ef | grep launch_new | grep -v grep | awk '{print $2, $1}'
