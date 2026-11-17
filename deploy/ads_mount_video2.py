# -*- coding: utf-8 -*-
"""v26 PMax 视频 mount 探测+重挂：查 Asset/AssetFieldType 枚举，试 YOUTUBE_VIDEO。"""
import os

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
ASSET = f"customers/{CID}/assets/437944129336"
AG_RN = f"customers/{CID}/assetGroups/6770847164"

# 1. Asset message 字段
from google.ads.googleads import v26  # noqa: E402
fields = [f.name for f in v26.resources.Asset.meta.fields.values()] \
    if hasattr(v26.resources.Asset, "meta") else []
print("Asset fields:", fields)

# 2. AssetFieldType 枚举
names = [n for n in dir(v26.enums.AssetFieldTypeEnum.AssetFieldType)
         if n.isupper()]
print("AssetFieldType:", names)

from google.ads.googleads.client import GoogleAdsClient  # noqa: E402
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
aga = client.get_service("AssetGroupAssetService")

# 3. 试 YOUTUBE_VIDEO field_type 挂载
op2 = client.get_type("AssetGroupAssetOperation")
op2.create.asset_group = AG_RN
op2.create.asset = ASSET
op2.create.field_type = "YOUTUBE_VIDEO"
op2.create.status = "ENABLED"
try:
    aga.mutate_asset_group_assets(customer_id=CID, operations=[op2])
    print("MOUNT OK: YOUTUBE_VIDEO")
except Exception as e:  # noqa: BLE001
    print("YOUTUBE_VIDEO 挂载失败:", str(e)[:500])
    raise SystemExit(1)

# 4. readback
from collections import Counter  # noqa: E402
gas = client.get_service("GoogleAdsService")
q = ("SELECT asset_group_asset.field_type, asset_group_asset.status "
     "FROM asset_group_asset "
     f"WHERE asset_group_asset.asset_group = '{AG_RN}'")
cnt = Counter(f"{x.asset_group_asset.field_type.name}/{x.asset_group_asset.status.name}"
              for x in gas.search(customer_id=CID, query=q))
print("Readback:", dict(cnt))
q2 = ("SELECT asset_group.ad_strength FROM asset_group "
      f"WHERE asset_group.resource_name = '{AG_RN}'")
for row in gas.search(customer_id=CID, query=q2):
    print("ad_strength:", row.asset_group.ad_strength.name)
