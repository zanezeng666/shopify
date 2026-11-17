#!/bin/bash
# 后台打标启动器
cd /home/jason/shopify-admin
sudo -u jason env HOME=/home/jason .venv/bin/python deploy/apply_ad_ready.py > deploy/ad_tag.log 2>&1
