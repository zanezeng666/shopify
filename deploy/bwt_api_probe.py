# -*- coding: utf-8 -*-
"""BWT API 探查 v3：基址已确认可用，拉取站点核心数据。只读。"""
import json
import urllib.parse

import httpx

KEY = "2ea6064fe1324a07be26c44d6a2c094c"
BASE = "https://ssl.bing.com/webmaster/api.svc/json"
SITE = "https://www.estrybattery.com/"


def call(name, extra=None):
    p = {"apikey": KEY, "siteUrl": SITE}
    if extra:
        p.update(extra)
    r = httpx.get(f"{BASE}/{name}", params=p, timeout=30)
    body = r.text
    try:
        body = json.dumps(r.json(), ensure_ascii=False)[:1600]
    except Exception:
        body = body[:300]
    print(f"\n== {name}: HTTP {r.status_code} ==\n{body}")


for name in ["GetCrawlStats", "GetPageStats", "GetUrlTraffic",
             "GetKeywordStats", "GetSites"]:
    try:
        call(name)
    except Exception as e:
        print(f"{name}: 异常 {e}")
