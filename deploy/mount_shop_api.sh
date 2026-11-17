#!/bin/bash
# 将 shop_api.conf 挂载到主 nginx.conf（最小改动：仅加一行 include），带备份与全站回归
set -e
CONF=/usr/local/nginx-1.30.2/conf/nginx.conf
BAK=/usr/local/nginx-1.30.2/conf/nginx.conf.bak-20261102

echo "== 0. backup (skip if exists) =="
ls /usr/local/nginx-1.30.2/conf/shop_api.conf >/dev/null || { echo "FATAL: shop_api.conf missing"; exit 1; }
[ -f "$BAK" ] || cp "$CONF" "$BAK"
echo "backup ok: $BAK"

echo "== 1. insert one include line (idempotent) =="
grep -q 'include shop_api.conf;' "$CONF" || sed -i '/include cloudflare_real_ip.conf;/a\    include shop_api.conf;' "$CONF"
grep -n 'shop_api' "$CONF"

echo "== 2. nginx -t =="
/usr/local/nginx-1.30.2/sbin/nginx -t -c "$CONF"

echo "== 3. reload =="
/usr/local/nginx-1.30.2/sbin/nginx -s reload -c "$CONF"

echo "== 4. regression: all existing sites + new =="
sleep 2
echo "bornmieo.com    : $(curl -sk -m 5 -o /dev/null -w '%{http_code}' https://127.0.0.1/ -H 'Host: bornmieo.com')"
echo "www.bornmieo.com: $(curl -sk -m 5 -o /dev/null -w '%{http_code}' https://127.0.0.1/ -H 'Host: www.bornmieo.com')"
echo "factory.bornmieo: $(curl -sk -m 5 -o /dev/null -w '%{http_code}' https://127.0.0.1/ -H 'Host: factory.bornmieo.com')"
echo "shopify-api     : $(curl -sk -m 5 --resolve shopify-api.bornmieo.com:443:127.0.0.1 https://shopify-api.bornmieo.com/health)"
echo DONE
