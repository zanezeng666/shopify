# -*- coding: utf-8 -*-
"""定位 MC 报"目标网址无效"的 4 类商品在 Shopify 的状态。
两类命中：标题关键词 or product_type；输出 handle/status/线上可达性。"""
import sys

import httpx

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text

from shopify_admin.core.database import get_engine

KW = ["camera", "gps", "navigator", "smartphone", "mobile phone",
      "ebook", "ereader", "e-reader"]
TYPES = ["Camera Battery", "GPS, Navigator Battery",
         "Mobile SmartPhone Battery", "Ebook, eReader Battery"]

eng = get_engine()
with eng.connect() as c:
    # 宽匹配：title 或 product_type 命中关键词
    like_t = " OR ".join(["title LIKE :kw" for _ in KW])
    like_p = " OR ".join(["product_type LIKE :kw" for _ in KW])
    params = {f"kw{i}": f"%{k}%" for i, k in enumerate(KW)}
    q = text(
        "SELECT id, handle, title, product_type, status FROM products "
        f"WHERE ({like_t}) OR ({like_p})".replace(":kw", ":kw0")
    ) if False else text(
        "SELECT id, handle, title, product_type, status FROM products "
        "WHERE " + " OR ".join(
            [f"title LIKE :k{i}" for i in range(len(KW))]
            + [f"product_type LIKE :k{i}" for i in range(len(KW))]),
    )
    params = {f"k{i}": f"%{k}%" for i, k in enumerate(KW)}
    rows = c.execute(q, params).all()

print(f"命中 {len(rows)} 个产品")
from collections import Counter

by_status = Counter(r[4] for r in rows)
by_type = Counter(r[3] for r in rows)
print("status:", dict(by_status))
print("product_type top:", by_type.most_common(10))

# 抽样：每类每状态取前几个测线上可达性
samples = {}
for pid, handle, title, ptype, status in rows:
    key = (ptype or "?", status)
    samples.setdefault(key, [])
    if len(samples[key]) < 3 and handle:
        samples[key].append(handle)

print("\n=== 抽样 HTTP 实测（每 product_type×status 抽 3）===")
with httpx.Client(
    timeout=20, follow_redirects=True,
    headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
              "AppleWebKit/537.36 Chrome/120 Safari/537.36"},
) as hc:
    for (ptype, status), hs in sorted(samples.items()):
        for h in hs:
            u = f"https://www.estrybattery.com/products/{h}"
            try:
                r = hc.get(u)
                ok = r.status_code == 200 and "estry" in r.text.lower()[:5000]
                code = r.status_code
            except Exception as e:  # noqa
                code, ok = f"ERR:{type(e).__name__}", False
            print(f"  [{status:8}] {ptype[:28]:28} {code} "
                  f"{'OK' if ok else 'BAD'} /products/{h[:60]}")
