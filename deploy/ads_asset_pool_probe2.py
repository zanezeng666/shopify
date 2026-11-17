# -*- coding: utf-8 -*-
"""全量拉账号 asset 文本，品牌词匹配，命中即候选删除。"""
import os

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

print("=== 账号级 asset 全量（resource_name + 文本） ===")
try:
    rs = list(gas.search(
        customer_id=CID,
        query="SELECT asset.resource_name, asset.name, "
              "asset.text_asset.text FROM asset"))
    print(f"  asset 总数: {len(rs)}")
except Exception as e:  # noqa: BLE001
    print(f"  ✗ 基础查询也失败: {str(e)[:120]}")
    raise SystemExit

BRAND = ("jbl", "bose", "soundlink", "craftsman", "nextec",
         "styles:", "flip 4", "flip4", "dremel", "ryobi", "dewalt",
         "makita", "milwaukee", "cameron", "cameron sino")
hits = []
for r in rs:
    t = (r.asset.text_asset.text or "").strip()
    if t and any(w in t.lower() for w in BRAND):
        hits.append((r.asset.resource_name, t))

print(f"\n品牌词命中: {len(hits)}")
for rn, t in hits[:20]:
    print(f"  {t[:66]}")
    print(f"    {rn}")
if not hits:
    print("账号 asset 池中无品牌词文本（AI 素材不在池内）")
