#!/bin/bash
# vendor 批改后台启动器
cd /home/jason/shopify-admin
sudo -u jason env HOME=/home/jason .venv/bin/python deploy/vendor_fix.py > deploy/vendor_fix_stdout.log 2>&1 &
echo "vendor_fix started pid=$!"
