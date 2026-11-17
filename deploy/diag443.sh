#!/bin/bash
echo "=== listening 443/80/8443 ==="
ss -tlnp | grep -E ':(443|80|8443) '
echo "=== main nginx.conf structure ==="
grep -n 'listen\|server_name\|include\|proxy_pass\|return' /usr/local/nginx-1.30.2/conf/nginx.conf
echo "=== 8443 referenced in main conf? ==="
grep -n '8443' /usr/local/nginx-1.30.2/conf/nginx.conf || echo NO-REF
echo "=== pid files ==="
ls -la /usr/local/nginx-1.30.2/logs/nginx.pid 2>/dev/null
