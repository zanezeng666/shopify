# -*- coding: utf-8 -*-
"""IndexNow 提交死链（Bing 重爬 404 后移除索引）。"""
import json
import time

import httpx

st = json.load(open("/home/jason/shopify-admin/deploy/idxnow_state.json"))
dead = json.load(open("/home/jason/shopify-admin/deploy/bwt_deadlinks.json"))
if not dead:
    print("无死链")
    raise SystemExit
r = httpx.post("https://api.indexnow.org/indexnow",
               headers={"User-Agent": "Mozilla/5.0 (compatible; EstryIndexnow/1.0)",
                        "Content-Type": "application/json; charset=utf-8"},
               json={"host": "www.estrybattery.com",
                     "key": st["key"], "urlList": dead}, timeout=60)
print(f"死链 {len(dead)} 个 -> HTTP {r.status_code} {r.text[:200]}")
