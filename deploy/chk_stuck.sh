#!/bin/bash
# 卡点全景：进程/日志/.env 代理与超时/settings 实际值
echo "=== 进程 ==="
pgrep -f run_pricing_apply || echo EXITED
PY=$(pgrep -f run_pricing_apply | tail -1)
if [ -n "$PY" ]; then
  ps -p $PY -o pid,etime,time,stat --no-headers
  echo "syscall: $(cat /proc/$PY/syscall 2>/dev/null | cut -c1-60)"
fi
echo "=== 日志 mtime/大小 ==="
stat -c '%y %s' /tmp/pricing_apply.log
echo "=== 日志尾部 ==="
tail -8 /tmp/pricing_apply.log
echo "=== 当前时间 ==="
date '+%F %T'
echo "=== .env 代理/超时相关 ==="
grep -iE 'proxy|timeout' /home/jason/shopify-admin/.env || echo "no proxy/timeout lines"
echo "=== settings 实际值 ==="
cd /home/jason/shopify-admin && sudo -u jason .venv/bin/python - <<'EOF'
import sys
sys.path.insert(0, "src")
from shopify_admin.config import settings
for k in ("shopify_proxy", "shopify_api_timeout", "shopify_retry_max", "shopify_domain", "pricing_margin_floor"):
    print(k, "=", getattr(settings, k, "<absent>"))
EOF
