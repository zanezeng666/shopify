# -*- coding: utf-8 -*-
"""用 /tmp/new_refresh.txt 更新 .env 的 GOOGLE_REFRESH_TOKEN（先备份）"""
import shutil
from datetime import date

ENV = "/home/jason/shopify-admin/.env"
bak = f"{ENV}.bak_oauth_{date.today():%Y%m%d}"
shutil.copy2(ENV, bak)
new_rt = open("/tmp/new_refresh.txt").read().strip()

lines = open(ENV, encoding="utf-8").read().splitlines(keepends=False)
hit = False
for i, ln in enumerate(lines):
    if ln.startswith("GOOGLE_REFRESH_TOKEN="):
        lines[i] = f"GOOGLE_REFRESH_TOKEN={new_rt}"
        hit = True
if not hit:
    lines.append(f"GOOGLE_REFRESH_TOKEN={new_rt}")
open(ENV, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("backup:", bak)
print("GOOGLE_REFRESH_TOKEN updated:", hit, f"({new_rt[:8]}...)")
