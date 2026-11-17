#!/bin/bash
# GPS RSA 每小时重试，最多48次；成功即退出
for i in $(seq 1 48); do
  echo "=== attempt $i $(date)" >> /tmp/gps_retry.log
  sudo -u jason env HOME=/home/jason \
    /home/jason/shopify-admin/.venv/bin/python \
    /home/jason/shopify-admin/deploy/gps_rsa_retry.py \
    >> /tmp/gps_retry.log 2>&1
  if [ $? -eq 0 ]; then
    echo "DONE $(date)" >> /tmp/gps_retry.log
    break
  fi
  sleep 3600
done
