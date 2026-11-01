# -*- coding: utf-8 -*-
"""探测 cameronsino.co 产品图片外链规律: https://cameronsino.co/images/CS-{id}-{N}.jpg

- 样本: 用户给定的 CS-EZP300SL + Shopify 老品实证编号 + cs_new 随机取若干
- 逐编号 HEAD 探测 N=1..MAX_N, 首个 404/无效即停(验证连续性)
- 直连失败自动走 SHOPIFY_PROXY
"""
import os
import sys
from pathlib import Path

import pymysql
import httpx

BASE = "https://cameronsino.co/images"
MAX_N = 12
PROXY = os.environ.get("SHOPIFY_PROXY", "http://127.0.0.1:7897")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}


def db_sample(n: int = 12) -> list[str]:
    env = Path(__file__).resolve().parents[1] / ".env"
    cfg: dict[str, str] = {}
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    conn = pymysql.connect(
        host=cfg["CS_DB_HOST"], port=int(cfg["CS_DB_PORT"]),
        user=cfg["CS_DB_USER"], password=cfg["CS_DB_DB_PASSWORD" if False else "CS_DB_PASSWORD"],
        database=cfg["CS_DB_NAME"], charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT cs_id FROM cs_product "
                "WHERE cs_id LIKE 'CS-%%' ORDER BY RAND() LIMIT %s", (n,))
            return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def probe(ids: list[str]) -> None:
    # 先试直连, 失败换代理
    for proxy in (None, PROXY):
        try:
            with httpx.Client(
                timeout=10, follow_redirects=True,
                proxy=proxy if proxy else None, headers=HEADERS,
            ) as c:
                r = c.head(f"{BASE}/CS-EZP300SL-1.jpg")
                print(f"[连通性] proxy={proxy or '直连'} -> {r.status_code}")
                if r.status_code in (200, 301, 302, 403):
                    run_all(ids, c)
                    return
        except Exception as e:  # noqa: BLE001
            print(f"[连通性] proxy={proxy or '直连'} 异常: {e}")
    print("!! 直连与代理均不可用")


def run_all(ids: list[str], c: httpx.Client) -> None:
    print(f"\n{'cs_id':<16}{'图片数':>4}  URLs")
    for cs_id in ids:
        urls: list[str] = []
        for n in range(1, MAX_N + 1):
            url = f"{BASE}/{cs_id}-{n}.jpg"
            try:
                r = c.head(url)
                ok = r.status_code == 200
            except Exception:  # noqa: BLE001
                ok = False
            if ok:
                urls.append(url)
            else:
                break  # 编号连续, 首个 miss 即停
        n = len(urls)
        span = f"{urls[0]} .. -{n}.jpg" if n else "无"
        print(f"{cs_id:<16}{n:>4}  {span}")


if __name__ == "__main__":
    fixed = ["CS-EZP300SL", "CS-BTR100MX", "CS-CNM200SL", "CS-RTK300MD", "CS-2HCFX2NR"]
    sample = db_sample(int(sys.argv[1]) if len(sys.argv) > 1 else 12)
    ids = [i for i in fixed + sample]
    print(f"样本 {len(ids)} 个: {ids}\n")
    probe(ids)
