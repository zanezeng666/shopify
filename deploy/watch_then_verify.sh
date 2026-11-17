#!/bin/sh
# 清码完成 -> 自动跑终验
while ! grep -q 清码完成 /home/jason/shopify-admin/deploy/barcode_clear.log; do
    sleep 60
done
sleep 30
cd /home/jason/shopify-admin
sudo -u jason env HOME=/home/jason .venv/bin/python deploy/verify_ready.py \
    > deploy/verify_ready.log 2>&1
echo VERIFY_DONE >> deploy/verify_ready.log
