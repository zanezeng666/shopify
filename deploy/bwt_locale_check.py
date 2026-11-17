# -*- coding: utf-8 -*-
"""多语言 SEO 验证：主域 vs en-ca 的 canonical/hreflang/title + SEO title 修复进度。只读。"""
import json
import re

import httpx

UA = {"User-Agent": "Mozilla/5.0 (compatible; EstrySEOCheck/1.0)"}
allp = json.load(open("/home/jason/shopify-admin/deploy/bwt_audit_result.json"))
done = json.load(open("/home/jason/shopify-admin/deploy/bwt_title_fix_done.json"))
print(f"SEO title 修复进度: {len(done)} / 2791")

sample = next(p for p in allp
              if p["title"].startswith("Battery for 2GIG GC3 Panel")
              and p["id"] in done)
h = sample["handle"]
for u in [f"https://www.estrybattery.com/products/{h}",
          f"https://www.estrybattery.com/en-ca/products/{h}"]:
    try:
        r = httpx.get(u, headers=UA, timeout=30, follow_redirects=True)
        html = r.text
        title = re.search(r"<title>(.*?)</title>", html)
        canon = re.search(r'<link rel="canonical" href="(.*?)"', html)
        langs = re.findall(r'<link rel="alternate" hreflang="(.*?)" href="(.*?)"',
                           html)
        print(f"\nHTTP {r.status_code} {u}")
        print(f"  title   : {(title.group(1) if title else '?')[:70]}")
        print(f"  canonical: {canon.group(1) if canon else '?'}")
        for lg, lu in langs[:6]:
            print(f"  hreflang {lg}: {lu[:70]}")
    except Exception as e:
        print(f"\n{u} 异常 {e}")
