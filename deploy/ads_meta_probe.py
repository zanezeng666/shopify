# -*- coding: utf-8 -*-
"""用 google_ads_field 元数据查 shopping_performance_view 可选字段。"""
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
fsvc = client.get_service("GoogleAdsFieldService")


def fields_like(pattern):
    req = client.get_type("SearchGoogleAdsFieldsRequest")
    req.query = (f"SELECT name, selectable "
                 f"WHERE name LIKE '{pattern}'")
    return list(fsvc.search_google_ads_fields(request=req))


print("=== shopping_performance_view 字段 ===")
try:
    rs = fields_like("shopping_performance_view.%")
    for f in rs:
        print(f"  {f.name} (selectable={f.selectable})")
    if not rs:
        print("  无字段——该视图在 v26 不存在")
except Exception as e:  # noqa: BLE001
    s = str(e)
    i = s.find("errors {")
    print(f"✗ {s[i:i+260] if i >= 0 else s[:160]}")

# 顺带查 product 相关视图/资源
print("\n=== product* 资源字段探查 ===")
for res in ("product_item_view.%", "product_group.%"):
    try:
        rs2 = fields_like(res)
        names = [f.name for f in rs2][:8]
        print(f"  {res}: {names if names else '不存在'}")
    except Exception as e:  # noqa: BLE001
        print(f"  {res}: 查询失败 {str(e)[:80]}")
