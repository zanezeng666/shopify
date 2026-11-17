# -*- coding: utf-8 -*-
"""IndexNow 每日增量：抓 sitemap 全量 URL，与已提交集合取差集，新 URL 提交并更新 state。
幂等：首跑把全量存为基数（差集为空不提交）。"""
import json
import re
import sys
import time

import httpx

HOST = "www.estrybattery.com"
STATE = "/home/jason/shopify-admin/deploy/idxnow_state.json"
API = "https://api.indexnow.org/indexnow"
UA = {"User-Agent": "Mozilla/5.0 (compatible; EstryIndexnow/1.0)"}

with open(STATE) as f:
    st = json.load(f)
key = st["key"]
done = set(st.get("submitted", []))

idx = httpx.get(f"https://{HOST}/sitemap.xml", headers=UA, timeout=60,
                follow_redirects=True)
shards = list(dict.fromkeys(
    s for s in re.findall(r"<loc>(.*?)</loc>", idx.text) if "sitemap" in s))
urls = set()
for s in shards:
    for attempt in range(3):
        try:
            r = httpx.get(s, headers=UA, timeout=90, follow_redirects=True)
            urls.update(u for u in re.findall(r"<loc>(.*?)</loc>", r.text)
                        if u.startswith("https://"))
            break
        except Exception:
            time.sleep(3)

new = sorted(urls - done)
print(f"{time.strftime('%F %T')} sitemap={len(urls)} 已提交={len(done)} "
      f"新增={len(new)}")

if new:
    B = 8000
    sent = 0
    for i in range(0, len(new), B):
        r = httpx.post(API,
                       headers={**UA, "Content-Type": "application/json; charset=utf-8"},
                       json={"host": HOST, "key": key, "urlList": new[i:i + B]},
                       timeout=120)
        print(f"  批 {i//B+1}: {len(new[i:i+B])} URL -> HTTP {r.status_code}")
        if r.status_code in (200, 202):
            sent += len(new[i:i + B])
        time.sleep(2)
    if sent:
        done |= set(new[:sent])
        with open(STATE, "w") as f:
            json.dump({**st, "submitted": sorted(done),
                       "last_submit": time.strftime("%F %T")}, f)
        print(f"  增量提交 {sent}，state 已更新")
else:
    if not done:  # 首跑建基数
        with open(STATE, "w") as f:
            json.dump({**st, "submitted": sorted(urls),
                       "last_submit": time.strftime("%F %T")}, f)
        print("  首跑建基数完成，未提交（全量已由 setup 脚本交过）")
