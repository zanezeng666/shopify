# -*- coding: utf-8 -*-
"""BWT 单页问题诊断：首页无alt图片/多h1 + all集合description + title修复终态。只读。"""
import json
import re

import httpx

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/119.0.0.0 Safari/537.36"}

# 0. title 修复终态
done = json.load(open("/home/jason/shopify-admin/deploy/bwt_title_fix_done.json"))
print(f"SEO title 修复终态: {len(done)} 个（目标 2791）")

# 1. 首页
r = httpx.get("https://www.estrybattery.com/", headers=UA, timeout=30,
              follow_redirects=True)
print(f"\n首页 HTTP {r.status_code}")
html = r.text
imgs = re.findall(r"<img[^>]*>", html)
noalt = [t for t in imgs if not re.search(r'alt\s*=', t, re.I)]
print(f"img 总数 {len(imgs)}，无 alt {len(noalt)}:")
for t in noalt:
    print(f"  {t[:160]}")
h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.S)
print(f"\nh1 数量 {len(h1s)}:")
for h in h1s:
    print(f"  <h1>{re.sub(r'<[^>]+>|\\s+', ' ', h)[:80]}</h1>")

# 2. /collections/all
r2 = httpx.get("https://www.estrybattery.com/collections/all", headers=UA,
               timeout=30, follow_redirects=True)
print(f"\n/collections/all HTTP {r2.status_code}")
md = re.search(r'<meta name="description" content="(.*?)"', r2.text)
print(f"meta description: {md.group(1)[:100] if md else '【缺失】'}")
title2 = re.search(r"<title>(.*?)</title>", r2.text)
print(f"title: {title2.group(1) if title2 else '?'}")
