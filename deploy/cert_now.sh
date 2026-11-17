#!/bin/bash
echo "=== 1. what cert does origin serve for each SNI now ==="
for h in www.bornmieo.com factory.bornmieo.com shopify-api.bornmieo.com; do
  echo "--- $h ---"
  echo | openssl s_client -connect 127.0.0.1:443 -servername $h 2>/dev/null | openssl x509 -noout -subject -issuer -dates 2>/dev/null
done

echo ""
echo "=== 2. which cert files do live conf reference ==="
grep -n "ssl_certificate" /usr/local/nginx-1.30.2/conf/nginx.conf /usr/local/nginx-1.30.2/conf/shop_api.conf

echo ""
echo "=== 3. factory standalone cert validity (the one user remembers) ==="
openssl x509 -in /etc/nginx/ssl/factory.bornmieo.com.crt -noout -dates -issuer
