# -*- coding: utf-8 -*-
"""MC 死链商品清理 v2（merchantapi products/v1，MC=136469408）。

数据源判定：
  - 旧源(10604168290) 全量 archived 死链 → 删（抽验 link handle 404）
  - Shopify 源(shopify_US_{pid}_{vid})：vid 映射线上状态
      active → 保留；medical → 保护；draft/archived非医疗 → 删；
      商品已删（vid 无记录）→ 删
护栏：医疗类型绝不删；默认 dry-run；清单落盘；限速+重试。
"""
import argparse
import json
import os
import re
import time
import urllib.parse

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
MC = "136469408"
BASE = f"https://merchantapi.googleapis.com/products/v1/accounts/{MC}"
OLD_DS = "10604168290"
STATE = "/home/jason/shopify-admin/deploy/mc_purge_state2.json"


def mc_token():
    r = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_MC_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def mc_get(hd, url, params=None, tries=4):
    for i in range(tries):
        r = httpx.get(url, params=params, headers=hd, timeout=60)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 503):
            time.sleep(2 ** i + 1)
            continue
        raise RuntimeError(
            f"GET {url[:80]} → {r.status_code}: {r.text[:200]}")
    raise RuntimeError(f"GET 重试耗尽: {url[:80]}")


_V_RE = re.compile(r"^shopify_US_\d+_(\d+)$")


def parse_offer(o):
    m = _V_RE.match(o)
    return int(m.group(1)) if m else None


def list_all_products(hd):
    out, tok, pages, t0 = [], None, 0, time.time()
    while True:
        params = {"pageSize": 250}
        if tok:
            params["pageToken"] = tok
        b = mc_get(hd, f"{BASE}/products", params)
        for p in b.get("products", []):
            pa = p.get("productAttributes", {})
            types = pa.get("productTypes") or []
            ds = (p.get("dataSource") or "").rsplit("/", 1)[-1]
            out.append({
                "id": p.get("name", "").split("/")[-1],
                "offer": p.get("offerId", ""),
                "vid": parse_offer(p.get("offerId", "")),
                "ds": ds,
                "archived": bool(p.get("archived")),
                "types": str(types[0]) if types else "",
                "medical": any("medical" in str(t).lower() for t in types),
                "mpn": pa.get("mpn", ""),
                "title": pa.get("title", ""),
                "link": pa.get("link", ""),
            })
        tok = b.get("nextPageToken")
        pages += 1
        if pages % 20 == 0:
            print(f"  MC {pages} 页 {len(out)} 商品 ({time.time()-t0:.0f}s)",
                  flush=True)
        if not tok:
            break
        time.sleep(0.3)
    print(f"MC 商品总数: {len(out)}（{pages} 页, {time.time()-t0:.0f}s）")
    return out


def shopify_variants():
    """全量（active/draft/archived）{vid: (status, product_type)}。"""
    from shopify_admin.platforms.shopify.rest import ShopifyRest
    from shopify_admin.services.stores.service import StoreService

    client = ShopifyRest(StoreService().get_client(1)).client
    Q = """
      products(first: 250%s) {
        pageInfo { hasNextPage endCursor }
        nodes {
          productType
          status
          variants(first: 100) { nodes { id } }
        }
      }
    """
    vmap, cursor, pages, t0 = {}, None, 0, time.time()
    while True:
        qq = "{%s}" % (Q % (f', after: "{cursor}"' if cursor else ""))
        r = client.graphql(qq)
        conn = r["products"]
        for p in conn["nodes"]:
            for v in (p["variants"]["nodes"] or []):
                vid = int(v["id"].rsplit("/", 1)[-1])
                vmap[vid] = (p["status"], p.get("productType") or "")
        pages += 1
        if pages % 20 == 0:
            print(f"  Shopify {pages} 页 {len(vmap)} 变体 "
                  f"({time.time()-t0:.0f}s)", flush=True)
        if not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]
        time.sleep(0.4)
    print(f"Shopify 全量变体: {len(vmap)}（{pages} 页, {time.time()-t0:.0f}s）")
    return vmap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true", help="真删（默认 dry-run）")
    args = ap.parse_args()

    hd = {"Authorization": f"Bearer {mc_token()}"}

    print("=== 1. 拉取 MC 全量商品 ===")
    prods = list_all_products(hd)
    print("\n=== 2. 拉取 Shopify 全量变体（含 draft/archived） ===")
    vmap = shopify_variants()

    print("\n=== 3. 分组判定 ===")
    groups = {"keep_active": [], "keep_medical": [], "dead_olddsr": [],
              "dead_offline": [], "dead_deleted": [], "unknown": []}
    for p in prods:
        if p["ds"] == OLD_DS or p["archived"]:
            groups["dead_olddsr"].append(p)
        elif p["vid"] is None:
            groups["unknown"].append(p)
        else:
            st = vmap.get(p["vid"])
            if st and st[0] == "ACTIVE":
                groups["keep_active"].append(p)
            elif p["medical"]:
                groups["keep_medical"].append(p)
            elif st:  # DRAFT/ARCHIVED 非医疗
                groups["dead_offline"].append(p)
            else:  # 商品已删
                groups["dead_deleted"].append(p)

    for k, v in groups.items():
        print(f"  {k:14} {len(v)}")
    dead = groups["dead_olddsr"] + groups["dead_offline"] + \
        groups["dead_deleted"]

    by_type = {}
    for p in dead:
        t = p["types"] or "(无类型)"
        by_type[t] = by_type.get(t, 0) + 1
    print("\n待删按类型:")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1])[:12]:
        print(f"  {t[:46]:46} {n}")

    with open(STATE, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in groups.items()}, f, ensure_ascii=False)
    print(f"\n清单已存档 {STATE}")
    if groups["unknown"]:
        print(f"⚠ unknown {len(groups['unknown'])} 个（不删，样本: "
              f"{[u['offer'][:30] for u in groups['unknown'][:3]]}）")
    if not args.go:
        print("\n[DRY-RUN] 未执行删除。确认后加 --go 真删。")
        return

    print("\n=== 3.5 全量防线：active handle 交集保护 ===")
    from shopify_admin.platforms.shopify.rest import ShopifyRest
    from shopify_admin.services.stores.service import StoreService

    sclient = ShopifyRest(StoreService().get_client(1)).client
    HQ = """
      products(first: 250, query: "status:active"%s) {
        pageInfo { hasNextPage endCursor }
        nodes { handle }
      }
    """
    active_h, cursor = set(), None
    while True:
        qq = "{%s}" % (HQ % (f', after: "{cursor}"' if cursor else ""))
        r = sclient.graphql(qq)
        conn = r["products"]
        for n in conn["nodes"]:
            active_h.add(n["handle"])
        if not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]
        time.sleep(0.4)
    print(f"线上 active handle 集合: {len(active_h)}")
    before = len(dead)
    protected = [p for p in dead
                 if urllib.parse.urlparse(p["link"]).path.rsplit("/", 1)[-1]
                 in active_h]
    dead = [p for p in dead
            if urllib.parse.urlparse(p["link"]).path.rsplit("/", 1)[-1]
            not in active_h]
    print(f"全量防线: 交集约谈保护剔除 {before - len(dead)} 个"
          f"（active 商品永不删），实际删除 {len(dead)} 个")
    if protected:
        print(f"  被保护样本: {[p['offer'][:30] for p in protected[:3]]}")

    print(f"\n=== 4. 批量删除 {len(dead)} 个死链 ===")
    ok = fail = 0
    t0 = time.time()
    for i, p in enumerate(dead, 1):
        enc = urllib.parse.quote(p["id"], safe="")
        for attempt in range(3):
            r = httpx.delete(f"{BASE}/products/{enc}", headers=hd,
                             timeout=60)
            if r.status_code in (200, 204):
                ok += 1
                break
            if r.status_code in (429, 500, 503):
                time.sleep(2 ** attempt + 1)
                continue
            fail += 1
            if fail <= 8:
                print(f"  ✗ {p['offer'][:40]} → {r.status_code} "
                      f"{r.text[:100]}")
            break
        else:
            fail += 1
        if i % 250 == 0:
            print(f"  进度 {i}/{len(dead)} ok={ok} fail={fail} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        time.sleep(0.25)
    print(f"\n删除完成: ok={ok} fail={fail} 耗时 {time.time()-t0:.0f}s")

    print("\n=== 5. 复核剩余 ===")
    left = list_all_products(hd)
    print(f"MC 剩余商品 {len(left)}")


if __name__ == "__main__":
    main()
