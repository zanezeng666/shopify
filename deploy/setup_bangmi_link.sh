#!/bin/bash
# Estry 店（Bangmi 主体）接入体系收尾：CS_API_KEY 补配 + 调度开启 + systemd 化
set -euo pipefail

ENVF=/home/jason/shopify-admin/.env

echo "== 1) 提取 BMAI shopify key 并校验指纹 =="
key_line=$(grep -E '^SHOPIFY_API_KEY=' /root/bmai-keys.txt | head -1 || true)
if [ -z "$key_line" ]; then
  echo "keys file lines:"; sed -E 's/=.*/=***/' /root/bmai-keys.txt
  echo "FATAL: SHOPIFY_API_KEY 行不存在"; exit 1
fi
key=${key_line#SHOPIFY_API_KEY=}
fp=$(printf '%s' "$key" | sha256sum | cut -c1-12)
echo "fingerprint: $fp (expect 873b4d1910bc)"
[ "$fp" = "873b4d1910bc" ] || { echo "FATAL: 指纹不符"; exit 1; }

echo "== 2) .env 幂等合并 =="
sed -i '/^CS_API_KEY=/d; /^SCHEDULER_ENABLED=/d; /^SCHEDULER_AUTO_SUBMIT=/d' "$ENVF"
{
  echo "CS_API_KEY=$key"
  echo "SCHEDULER_ENABLED=true"
} >> "$ENVF"
chown jason:jason "$ENVF"; chmod 600 "$ENVF"
echo "env updated: CS_API_KEY=*** SCHEDULER_ENABLED=true (AUTO_SUBMIT 默认 false 只分仓不下单)"

echo "== 3) systemd unit =="
cat > /etc/systemd/system/shopify-admin-api.service <<'UNIT'
[Unit]
Description=Shopify Admin API (Estry store, Bangmi)
After=network.target

[Service]
User=jason
Group=jason
WorkingDirectory=/home/jason/shopify-admin
ExecStart=/home/jason/shopify-admin/.venv/bin/uvicorn shopify_admin.api.app:app --host 127.0.0.1 --port 8100
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

echo "== 4) 切换进程 =="
pkill -f 'uvicorn shopify_admin.api.app:app' || true
sleep 2
systemctl daemon-reload
systemctl enable --now shopify-admin-api
sleep 5
systemctl is-active shopify-admin-api
curl -fsS http://127.0.0.1:8100/health && echo
echo "DONE"
