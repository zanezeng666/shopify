# -*- coding: utf-8 -*-
"""抽样统计 cs_id 在 cameronsino.co 外链 -1.jpg 的命中率"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _probe_cs_images import BASE, HEADERS, db_sample  # noqa: E402

import httpx  # noqa: E402


def main(n: int) -> None:
    ids = db_sample(n)
    with httpx.Client(timeout=10, follow_redirects=True, headers=HEADERS) as c:
        miss = []
        for cs_id in ids:
            try:
                ok = c.head(f"{BASE}/{cs_id}-1.jpg").status_code == 200
            except Exception:  # noqa: BLE001
                ok = False
            if not ok:
                miss.append(cs_id)
    total = len(ids)
    print(f"sample={total} hit={total - len(miss)} rate={(total - len(miss)) / total:.0%}")
    print("miss:", miss)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 100)
