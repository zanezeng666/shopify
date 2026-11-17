# -*- coding: utf-8 -*-
"""验证小样 SEO title 线上生效 + 死链差集计算（IndexNow 曾提交过但现在非 active 的 URL）。"""
import json
import re
import sys
import urllib.parse

import httpx

sys.path.insert(0, "/home/jason/shopify-admin")

allp = json.load(open("/home/jason/shopify-admin/deploy/bwt_audit_result.json"))

# 1. 找小样产品（title 以 "Battery for 2GIG GC3" 开头的 active）
sample = next(p for p in allp
              if p["title"].startswith("Battery for 2GIG GC3 Panel"))
url = f"https://www.estrybattery.com/products/{sample['handle']}"
r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30,
              follow_redirects=True)
m = re.search(r"<title>(.*?)</title>", r.text)
print(f"HTTP {r.status_code} {url}")
print(f"  <title> = {m.group(1) if m else '未找到'}")
print(f"  原产品 title（h1 保持）= {sample['title'][:80]}...")

# 2. 死链差集：IndexNow submitted - active 产品 URL
st = json.load(open("/home/jason/shopify-admin/deploy/idxnow_state.json"))
submitted = set(st.get("submitted", []))
active_urls = {f"https://www.estrybattery.com/products/{p['handle']}"
               for p in allp if p["status"] == "active"}
dead = sorted(u for u in submitted
              if u.startswith("https://www.estrybattery.com/products/")
              and u not in active_urls)
print(f"\nIndexNow 曾提交 {len(submitted)}（去重后）")
print(f"当前 active 产品 URL {len(active_urls)}")
print(f"提交过但已非 active（死链）: {len(dead)}")
for u in dead[:5]:
    print(f"  {u}")

with open("/home/jason/shopify-admin/deploy/bwt_deadlinks.json", "w") as f:
    json.dump(dead, f)
print("死链清单已存 deploy/bwt_deadlinks.json")
