#!/bin/bash
# shopify-admin 持久化部署：systemd + nginx 子域反代（幂等）
set -e
echo "== 1. stop temp uvicorn =="
pkill -f 'uvicorn shopify_admin.api.app' || true
sleep 1

echo "== 2. install systemd unit =="
cp /home/jason/deploy/shopify-admin.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable shopify-admin 2>/dev/null
systemctl restart shopify-admin
sleep 3
echo "service: $(systemctl is-active shopify-admin)"

echo "== 3. install nginx conf =="
cp /home/jason/deploy/shopify-api.bornmieo.com.conf /usr/local/nginx-1.30.2/conf/shop_api.conf
grep -q 'include shop_api.conf;' /usr/local/nginx-1.30.2/conf/nginx-8443.conf || \
  sed -i '/include .*cloudflare_real_ip/a\    include shop_api.conf;' /usr/local/nginx-1.30.2/conf/nginx-8443.conf

echo "== 4. nginx test + reload =="
/usr/local/nginx-1.30.2/sbin/nginx -t -c /usr/local/nginx-1.30.2/conf/nginx-8443.conf
/usr/local/nginx-1.30.2/sbin/nginx -s reload -c /usr/local/nginx-1.30.2/conf/nginx-8443.conf

echo "== 5. verify =="
sleep 2
echo "service     : $(systemctl is-active shopify-admin)"
echo "local-health: $(curl -s -m 5 http://127.0.0.1:8100/health)"
echo "https-direct: $(curl -sk -m 5 --resolve shopify-api.bornmieo.com:443:127.0.0.1 https://shopify-api.bornmieo.com/health)"
echo DONE
