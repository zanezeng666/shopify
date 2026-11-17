#!/bin/bash
set -e
SSL=/etc/nginx/ssl
SA=/usr/local/nginx-1.30.2/conf/shop_api.conf

echo "== 0. install cert files =="
install -m 644 /tmp/shopify-api.bornmieo.com_bundle.crt $SSL/
install -m 600 /tmp/shopify-api.bornmieo.com.key $SSL/

echo "== 1. validate: SAN / validity / key-match =="
openssl x509 -in $SSL/shopify-api.bornmieo.com_bundle.crt -noout -subject -issuer -dates -ext subjectAltName
CERT_MD=$(openssl x509 -in $SSL/shopify-api.bornmieo.com_bundle.crt -noout -pubkey | openssl md5)
KEY_MD=$(openssl pkey -in $SSL/shopify-api.bornmieo.com.key -pubout 2>/dev/null | openssl md5)
[ "$CERT_MD" = "$KEY_MD" ] && echo "KEY-MATCH-OK" || { echo "FATAL: key mismatch"; exit 1; }

echo "== 2. backup + switch shop_api.conf to new cert =="
cp $SA $SA.bak-20261102
sed -i 's#ssl_certificate     /etc/nginx/ssl/nginx.crt;#ssl_certificate     /etc/nginx/ssl/shopify-api.bornmieo.com_bundle.crt;#' $SA
sed -i 's#ssl_certificate_key /etc/nginx/ssl/nginx.key;#ssl_certificate_key /etc/nginx/ssl/shopify-api.bornmieo.com.key;#' $SA
grep ssl_certificate $SA

echo "== 3. nginx -t + reload =="
/usr/local/nginx-1.30.2/sbin/nginx -t -c /usr/local/nginx-1.30.2/conf/nginx.conf
/usr/local/nginx-1.30.2/sbin/nginx -s reload -c /usr/local/nginx-1.30.2/conf/nginx.conf
sleep 2

echo "== 4. regression: all sites =="
echo "bornmieo.com    : $(curl -sk -m 5 -o /dev/null -w '%{http_code}' https://127.0.0.1/ -H 'Host: bornmieo.com')"
echo "www.bornmieo.com: $(curl -sk -m 5 -o /dev/null -w '%{http_code}' https://127.0.0.1/ -H 'Host: www.bornmieo.com')"
echo "factory         : $(curl -sk -m 5 -o /dev/null -w '%{http_code}' https://127.0.0.1/ -H 'Host: factory.bornmieo.com')"
echo "shopify-api (strict TLS verify, no -k):"
curl -s -m 5 --resolve shopify-api.bornmieo.com:443:127.0.0.1 https://shopify-api.bornmieo.com/health && echo " <- TLS-TRUSTED-OK"
echo DONE
