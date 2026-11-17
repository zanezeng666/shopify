# -*- coding: utf-8 -*-
"""v5：完整一级菜单（含直链）+ 156 种 product_type 全清单。"""
import re
import sys

import httpx
from sqlalchemy import text

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.core.database import get_engine

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}
html = httpx.get("https://estrybattery.com/", headers=UA, follow_redirects=True,
                 timeout=30).text
hdr = re.search(r"<header.*?</header>", html, re.S)
h = hdr.group(0) if hdr else html

# 顶级：去重后按首次出现顺序输出所有 header 链接（含非 details 直链）
seen, seq = set(), []
for href, inner in re.findall(r'<a[^>]*href="((?:/collections/|/)[^"#]*)"[^>]*>(.*?)</a>',
                              h, re.S):
    txt = " ".join(re.sub(r"<[^>]+>", " ", inner).split())
    if not txt or href.startswith("/products"):
        continue
    k = (txt, href)
    if k not in seen:
        seen.add(k)
        seq.append(k)
print("== header 全部链接（顺序，含重复渲染去重）:")
for t, u in seq[:40]:
    print(f"   {t!r:38} {u[:64]}")

with get_engine().connect() as cx:
    rows = cx.execute(text(
        "SELECT product_type, COUNT(*) c FROM products "
        "WHERE store_id=1 GROUP BY product_type ORDER BY c DESC")).fetchall()
print(f"== 全部 {len(rows)} 种 product_type:")
for t, c in rows:
    print(f"   {t or '(空)':44} {c}")
