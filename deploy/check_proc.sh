#!/bin/bash
SUPID=$(pgrep -f "sudo -u jason" | head -1)
PY=$(pgrep -P "$SUPID" 2>/dev/null | head -1)
[ -z "$PY" ] && PY=$(pgrep -f "run_pricing_apply" | tail -1)
ps -o pid,ppid,etime,time,%cpu,rss,cmd --no-headers -p "$PY" 2>/dev/null || echo EXITED
