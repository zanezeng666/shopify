#!/bin/bash
echo "=== 1. current origin certs ==="
ls -la /etc/nginx/ssl/ 2>/dev/null
openssl x509 -in /etc/nginx/ssl/nginx.crt -noout -subject -issuer -dates 2>/dev/null

echo ""
echo "=== 2. acme tooling present? ==="
which certbot acme.sh 2>/dev/null; ls -d ~/.acme.sh /etc/letsencrypt 2>/dev/null || echo no-acme-tools

echo ""
echo "=== 3. SNI probes on origin 443 ==="
for h in www.bornmieo.com factory.bornmieo.com shopify-api.bornmieo.com; do
  printf "%-26s: " $h
  curl -sk -m 5 -o /dev/null -w "%{http_code}" --resolve $h:443:127.0.0.1 https://$h/ 2>/dev/null
  echo ""
done

echo ""
echo "=== 4. port 80 owner (http-01 feasibility) ==="
ss -tlnp | grep ":80 " | head -2

echo ""
echo "=== 5. fresh DNS view (public resolver no-cache) ==="
dig @8.8.8.8 +short shopify-api.bornmieo.com A
dig @223.5.5.5 +short shopify-api.bornmieo.com A
