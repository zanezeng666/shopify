# -*- coding: utf-8 -*-
"""卡点全景：进程/日志/.env 代理超时/settings 实际值（python 直接跑，绕开 bash 行尾问题）"""
import subprocess
import sys
import time
import os

LOG = "/tmp/pricing_apply.log"


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


print("=== 进程 ===")
out = sh("pgrep -f run_pricing_apply")
print(out or "EXITED")
if out:
    pid = out.split()[-1]
    print(sh(f"ps -p {pid} -o pid,etime,time,stat --no-headers"))
    try:
        print("syscall:", open(f"/proc/{pid}/syscall").read()[:60])
    except Exception as e:
        print("syscall: unreadable", e)

print("=== 日志 ===")
if os.path.exists(LOG):
    st = os.stat(LOG)
    print("mtime:", time.strftime("%F %T", time.localtime(st.st_mtime)), "size:", st.st_size)
    print("now  :", time.strftime("%F %T"))
    with open(LOG, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    print("--- tail 8 ---")
    for ln in lines[-8:]:
        print(ln.rstrip())
    print("--- round 行 ---")
    for ln in lines:
        if "round" in ln or "delist" in ln or "DONE" in ln or "ERROR" in ln:
            print(ln.rstrip())
else:
    print("LOG MISSING")

print("=== .env 代理/超时 ===")
env_path = "/home/jason/shopify-admin/.env"
if os.path.exists(env_path):
    hit = False
    for ln in open(env_path, encoding="utf-8", errors="replace"):
        if "proxy" in ln.lower() or "timeout" in ln.lower():
            print(ln.rstrip())
            hit = True
    if not hit:
        print("(no proxy/timeout lines)")

print("=== settings 实际值 ===")
sys.path.insert(0, "/home/jason/shopify-admin/src")
os.chdir("/home/jason/shopify-admin")
from shopify_admin.config import settings as S

for k in ("shopify_proxy", "shopify_api_timeout", "shopify_retry_max", "pricing_margin_floor"):
    print(k, "=", getattr(S, k, "<absent>"))
