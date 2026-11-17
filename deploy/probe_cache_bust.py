# -*- coding: utf-8 -*-
"""验证：带随机参数绕 CDN 缓存，看 meta description 是否变化。"""
import random
import re
import urllib.request

URL = "https://estrybattery.com/collections/medical-battery"
tag = random.randint(10**8, 10**9)

for label, url in (("裸 URL（走 CDN 缓存）", URL),
                   (f"?cachebust={tag}（绕缓存）", f"{URL}?v={tag}")):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    m = re.search(r'<meta name="description" content="([^"]*)"', html)
    print(f"[{label}]")
    print("  meta desc:", m.group(1)[:160] if m else "(无)")
    # Dawn banner 区可见文本是否含那串
    vis = re.search(r'<div[^>]*collection-hero__description[^>]*>(.{0,200}?)</div>', html, re.S)
    print("  banner 描述:", vis.group(1).strip()[:160] if vis else "(无 banner 描述块)")
    print("  页面含 Shaver 字样:", "Shaver" in html)
    print()
