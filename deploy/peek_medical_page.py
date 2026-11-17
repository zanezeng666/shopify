# -*- coding: utf-8 -*-
"""抓 /collections/medical-battery 页面：产品构成 + 子类入口。"""
import re
import sys
from collections import Counter

import httpx

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text as sql_text
from shopify_admin.core.database import get_engine

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}
r = httpx.get("https://estrybattery.com/collections/medical-battery",
              headers=UA, follow_redirects=True, timeout=30)
print("== 状态:", r.status_code)
titles = re.findall(r'class="[^"]*card__heading[^"]*"[^>]*>\s*<a[^>]*>(.*?)</a>',
                    r.text, re.S) or re.findall(
    r'<a[^>]*href="/products/[^"]*"[^>]*>\s*([A-Za-z][^<]{10,80})\s*</a>', r.text)
clean = [" ".join(t.split()) for t in titles]
print("== 页面产品数(首页卡片):", len(clean))
for t in clean[:12]:
    print("   ", t[:78])
kw = Counter()
for t in clean:
    for k in ("Shaver", "Toothbrush", "Magnifier", "Microscope", "Thermal",
              "Personal", "Medical", "Monitor", "Patient", "Infusion", "Oximeter"):
        if k.lower() in t.lower():
            kw[k] += 1
print("== 标题关键词:", dict(kw))
# 页面上所有 collections 链接（可能存在子类导航区块）
cols = []
for href in re.findall(r'href="(/collections/[a-z0-9-]+)"', r.text):
    if href not in cols:
        cols.append(href)
print("== 页面 collections 链接:", cols[:20])

# 本地库：Medical collection 关联产品数（镜像）
with get_engine().connect() as cx:
    try:
        n = cx.execute(sql_text(
            "SELECT COUNT(*) FROM product_collections pc JOIN collections c "
            "ON c.id=pc.collection_id AND c.store_id=1 "
            "WHERE c.handle='medical-battery'")).scalar()
        print("== 本地镜像 medical-battery 关联产品:", n)
    except Exception as e:
        print("本地镜像查询失败:", str(e)[:100])
