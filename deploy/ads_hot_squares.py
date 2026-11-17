# -*- coding: utf-8 -*-
"""PMax 资产组方图换为热销医疗产品 + 移除旧 Med SQ。

选品(近10天订单×库存扣减双指标):
  P756          Philips HeartStart FRx/Home 除颤电池  37单/10天
  P4626167922788 Cameron Nuflo MC-II 血气分析仪电池   23单/10天
  P4644569940068 Rainin EDP3 移液器电池               15单/10天
  P7840406470900 Philips Invivo 9065 监护仪电池       (保留, 品类广度)
"""
import os
import time

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG = f"customers/{CID}/assetGroups/6770847164"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
asvc = client.get_service("AssetService")
gsvc = client.get_service("AssetGroupAssetService")

PICKS = [4638407622756, 4626167922788, 4644569940068, 7840406470900]

# ---- 0) 已传 Hot SQ 资产复用（v2 方形版才可复用,首版未过1:1校验） ----
existing = {}
q0 = "SELECT asset.resource_name, asset.name FROM asset " \
     "WHERE asset.name LIKE 'Hot SQ2 %'"
for row in gas.search(customer_id=CID, query=q0):
    existing[row.asset.name] = row.asset.resource_name
if existing:
    print(f"已有 Hot SQ2 资产复用: {sorted(existing)}")

# ---- 1) Shopify 拉主图 ----
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

cl = ShopifyRest(StoreService().get_client(1)).client
ids = ",".join(str(x) for x in PICKS)
r = cl.request("GET", "products.json",
               params={"ids": ids, "fields": "id,title,images"})
prods = {p["id"]: p for p in r.get("products", [])}
print(f"Shopify 命中 {len(prods)}/4")
mime_map = {"image/jpeg": "IMAGE_JPEG", "image/png": "IMAGE_PNG"}

# ---- 2) 传新方图资产 "Hot SQ2 {pid}"（本地 pad 成 1:1 白底方图） ----
from io import BytesIO  # noqa: E402

from PIL import Image, ImageOps  # noqa: E402

created = []
for pid in PICKS:
    p = prods.get(pid)
    if not p or not p.get("images"):
        print(f"!! P{pid} 无图, 跳过")
        continue
    key = f"Hot SQ2 {pid}"
    if key in existing:
        created.append((pid, existing[key], p["title"]))
        print(f"  复用已有资产 {key}")
        continue
    url = p["images"][0]["src"]
    url += ("&" if "?" in url else "?") + "width=1200"
    resp = httpx.get(url, timeout=60, follow_redirects=True)
    if resp.status_code != 200:
        print(f"!! P{pid} 下载失败 http={resp.status_code}")
        continue
    try:
        img = Image.open(BytesIO(resp.content)).convert("RGB")
    except Exception as e:  # noqa: BLE001
        print(f"!! P{pid} 图解码失败 {str(e)[:80]}")
        continue
    img = ImageOps.contain(img, (1200, 1200))
    canvas = Image.new("RGB", (1200, 1200), (255, 255, 255))
    canvas.paste(img, ((1200 - img.width) // 2,
                       (1200 - img.height) // 2))
    buf = BytesIO()
    canvas.save(buf, "JPEG", quality=92)
    data = buf.getvalue()
    if len(data) > 4_500_000:
        print(f"!! P{pid} 方图过大 {len(data)}B")
        continue
    aop = client.get_type("AssetOperation")
    a = aop.create
    a.name = f"Hot SQ2 {pid}"
    a.type_ = client.enums.AssetTypeEnum.IMAGE
    a.image_asset.data = data
    a.image_asset.mime_type = client.enums.MimeTypeEnum.IMAGE_JPEG
    try:
        arn = asvc.mutate_assets(
            customer_id=CID, operations=[aop]).results[0].resource_name
    except Exception as e:  # noqa: BLE001
        print(f"!! P{pid} 资产上传失败: {str(e)[:180]}")
        continue
    created.append((pid, arn, p["title"]))
    print(f"  asset OK P{pid} {p['title'][:52]}")
    time.sleep(0.5)

if len(created) < 4:
    raise SystemExit(f"新方图仅 {len(created)}/4, 中止(不改动现有挂载)")

# ---- 3) 挂新方图 + 摘旧 Med SQ ----
ops = []
for pid, arn, _ in created:
    gop = client.get_type("AssetGroupAssetOperation")
    g = gop.create
    g.asset_group = AG
    g.asset = arn
    g.field_type = client.enums.AssetFieldTypeEnum.SQUARE_MARKETING_IMAGE
    ops.append(gop)

q = ("SELECT asset_group_asset.resource_name, asset.name "
     "FROM asset_group_asset "
     f"WHERE asset_group_asset.asset_group = '{AG}' "
     "AND asset_group_asset.field_type = 'SQUARE_MARKETING_IMAGE' "
     "AND asset.name LIKE 'Med SQ %'")
removed = []
for row in gas.search(customer_id=CID, query=q):
    rop = client.get_type("AssetGroupAssetOperation")
    rop.remove = row.asset_group_asset.resource_name
    ops.append(rop)
    removed.append(row.asset.name)
print(f"待摘旧方图: {removed}")

resp = gsvc.mutate_asset_group_assets(customer_id=CID, operations=ops)
print(f"mutate OK: +{len(created)} -{len(removed)}")

# ---- 4) readback ----
q2 = ("SELECT asset_group_asset.field_type, asset.name, "
      "asset_group_asset.status FROM asset_group_asset "
      f"WHERE asset_group_asset.asset_group = '{AG}' "
      "AND asset_group_asset.field_type = 'SQUARE_MARKETING_IMAGE'")
live = [(r.asset.name, r.asset_group_asset.status.name)
        for r in gas.search(customer_id=CID, query=q2)]
for n, s in live:
    print(f"  live: {n} [{s}]")
