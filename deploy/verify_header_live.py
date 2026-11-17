# -*- coding: utf-8 -*-
"""线上验证：公告条新文案 + 新导航结构渲染。"""
import re

import httpx

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}
html = httpx.get("https://estrybattery.com/", headers=UA, follow_redirects=True,
                 timeout=30).text
m = re.search(r'announcement-bar__message[^>]*>(.*?)</p>', html, re.S)
print("== 公告条:", " ".join(re.sub(r"<[^>]+>", " ", m.group(1)).split()) if m else "未找到")
hdr = re.search(r"<header.*?</header>", html, re.S)
h = hdr.group(0) if hdr else ""
dets = re.findall(r"<details[^>]*>(.*?)</details>", h, re.S)
tops = []
for det in dets:
    sm = re.search(r"<summary[^>]*>(.*?)</summary>", det, re.S)
    if sm:
        tops.append(" ".join(re.sub(r"<[^>]+>", " ", sm.group(1)).split()))
print("== 导航一级(details 下拉):", tops)
flat = re.findall(r'<a[^>]*href="(/collections/(?:medical-battery|all))"', h)
print("== Medical/ShopAll 直链存在:", set(flat) != set() or "无")
sub = re.findall(r'href="(/collections/[a-z0-9-]+)"', h)
print("== collections 链接总数(去重):", len(set(sub)))
print("== Laptop/Phone 入口:", "/collections/notebook-laptop-battery" in h,
      "/collections/mobile-smartphone-battery" in h)
