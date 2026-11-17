# -*- coding: utf-8 -*-
"""查调度器（库存/产品同步任务是否活跃）+ REST 方法清单。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify import rest

methods = [m for m in dir(rest.ShopifyRest) if not m.startswith("_")]
print("ShopifyRest methods:", methods)

from shopify_admin.config import settings

print("\nscheduler crons:")
for k in dir(settings):
    if k.startswith("scheduler_") and k.endswith("_cron"):
        print(f"  {k} = {getattr(settings, k)}")

# 调度器进程是否在跑（uvicorn/apscheduler）
import subprocess

r = subprocess.run(["ps", "-eo", "pid,user,etime,args"], capture_output=True, text=True)
for line in r.stdout.splitlines():
    if ("shopify" in line.lower() or "uvicorn" in line.lower()) and "grep" not in line:
        print("PROC:", line[:160])
