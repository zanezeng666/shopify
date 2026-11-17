#!/bin/bash
echo "=== 1. 直接问 .com 顶级权威：bornmieo.com 的 NS 是谁 ==="
dig @a.gtld-servers.net bornmieo.com NS +short

echo ""
echo "=== 2. 完整权威链 trace（根->.com->目标） ==="
dig +trace bornmieo.com NS 2>/dev/null | grep -iE "bornmieo" | tail -6

echo ""
echo "=== 3. factory.bornmieo.com 现在谁在服务（HTTP 响应头） ==="
curl -sI -m 8 https://factory.bornmieo.com 2>/dev/null | grep -iE "^server|^cf-ray|^http"

echo ""
echo "=== 4. factory 的 A 记录归属（104.21.x/172.67.x = Cloudflare 段） ==="
dig factory.bornmieo.com +noall +answer

echo ""
echo "=== 5. 对比：一条确实存在的记录 www ==="
dig www.bornmieo.com +noall +answer
