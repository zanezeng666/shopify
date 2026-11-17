#!/bin/bash
# 启动元字段全量灌入后台任务
cd /home/jason/shopify-admin
sudo -u jason nohup .venv/bin/python deploy/classify/enrich_metafields.py \
  > /tmp/classify_enrich.log 2>&1 < /dev/null &
echo "ENRICH-STARTED pid=$!"
