# -*- coding: utf-8 -*-
"""账号级 asset 池探针：找 origin=AUTOMATICALLY_CREATED 的文本素材。"""
import os
from collections import Counter

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")


def try_q(label, q):
    try:
        rs = list(gas.search(customer_id=CID, query=q))
        print(f"  ✓ {label}: {len(rs)} 行")
        return rs
    except Exception as e:  # noqa: BLE001
        s = str(e)
        key = "UNRECOGNIZED_FIELD" in s and "字段不可查" or s[:80]
        print(f"  ✗ {label}: {key}")
        return None


print("=== asset.origin 可用性 ===")
rs = try_q("origin 查询",
           "SELECT asset.resource_name, asset.origin, asset.name, "
           "asset.text_asset.text FROM asset LIMIT 1000")
if rs is not None:
    cnt = Counter(r.asset.origin.name for r in rs)
    print(f"  origin 分布(前1000): {dict(cnt)}")
    auto = [r for r in rs if r.asset.origin.name not in
            ("UNSPECIFIED", "UNKNOWN", "USER", "OUTPUT_ONLY")]
    for r in auto[:10]:
        print(f"    自动: {(r.asset.text_asset.text or r.asset.name)[:60]}")

print("\n=== asset.type 过滤 TEXT + LIKE 找品牌词 ===")
rs2 = try_q("type=TEXT 全量",
            "SELECT asset.resource_name, asset.origin, "
            "asset.text_asset.text FROM asset "
            "WHERE asset.type = 'TEXT'")
if rs2 is not None:
    cnt = Counter(r.asset.origin.name for r in rs2)
    print(f"  TEXT 素材 origin 分布: {dict(cnt)}（共 {len(rs2)}）")
    brand_words = ("JBL", "Bose", "Bose Soundlink", "Craftsman",
                   "Nextec", "Styles", "Flip 4")
    hits = [r for r in rs2 if any(w.lower() in
            (r.asset.text_asset.text or "").lower() for w in brand_words)]
    print(f"  品牌词命中: {len(hits)}")
    for r in hits[:10]:
        print(f"    [{r.asset.origin.name}] {r.asset.text_asset.text[:64]}")
