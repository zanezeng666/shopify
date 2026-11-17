#!/bin/bash
PY=$(pgrep -f "run_pricing_apply" | tail -1)
[ -z "$PY" ] && { echo EXITED; exit 0; }
echo "pid=$PY"
echo "== 当前 syscall =="
cat /proc/$PY/syscall 2>/dev/null
echo "== 日志 mtime/大小（两次间隔 12s） =="
stat -c '%y %s' /tmp/pricing_apply.log
sleep 12
stat -c '%y %s' /tmp/pricing_apply.log
echo "== CPU 时间（两次） =="
awk '{print "utime+stime(ticks):", $14+$15}' /proc/$PY/stat
sleep 12
awk '{print "utime+stime(ticks):", $14+$15}' /proc/$PY/stat
echo "== mysql 侧当前查询（CDB processlist） =="
cd /home/jason/shopify-admin && sudo -u jason .venv/bin/python - <<'EOF'
import sys
sys.path.insert(0, "src")
from sqlalchemy import text
from shopify_admin.core.database import get_engine
with get_engine().connect() as c:
    rows = c.execute(text("SHOW PROCESSLIST")).all()
    for r in rows:
        if r[4] != 'Sleep' and 'processlist' not in str(r[7]):
            print(" ", r[0], r[3], str(r[7])[:120])
EOF
