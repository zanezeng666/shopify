# -*- coding: utf-8 -*-
"""索引抢救：sitemap lastmod 稳定性观测（纯只读）。

用途：vendor_fix（11-08）结束后验证 sitemap 不再全量刷新。
判读：
- 11-09 基线：全子表 lastmod 集中在 11-08（批处理日）
- 稳定后：仅少数 URL 的 lastmod 为当日（真实变更：改价 delist 等）
"""
from __future__ import annotations

import re
import sys
import urllib.request

BASE = "https://www.estrybattery.com/sitemap_products_{n}.xml"
SM_INDEX = "https://www.estrybattery.com/sitemap.xml"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "sitemap-watch/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def main() -> None:
    idx = fetch(SM_INDEX)
    subs = re.findall(r"<loc>(https://[^<]+/sitemap_products_\d+\.xml[^<]*)</loc>", idx)
    print(f"产品子表数: {len(subs)}")
    total = today = 0
    dist: dict[str, int] = {}
    for u in subs[:5] + subs[-5:]:   # 抽首尾各5个子表
        xml = fetch(u.replace("&", "&amp;")) if "&amp;" not in u else fetch(u)
        dates = re.findall(r"<lastmod>(\d{4}-\d{2}-\d{2})", xml)
        for d in dates:
            dist[d] = dist.get(d, 0) + 1
        total += len(dates)
    print(f"抽样 URL: {total}")
    for d in sorted(dist, reverse=True)[:7]:
        print(f"  {d}: {dist[d]}  ({dist[d] * 100.0 / total:.1f}%)")


if __name__ == "__main__":
    sys.exit(main())
