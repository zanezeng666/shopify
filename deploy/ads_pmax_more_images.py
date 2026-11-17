# -*- coding: utf-8 -*-
"""PMax Medical 资产组补产品图（提升 ad_strength POOR）。

现状: 资产组仅 1 MK + 1 SQ 图 → ad_strength=POOR 限制覆盖。
方案: 从 Shopify medical-battery collection 取产品主图（正方形白底），
      排除条码风险产品(barcode_scan_result.jsonl)，上传 4 张为
      SQUARE_MARKETING_IMAGE 附加图（多图轮换提升强度）。
断点: deploy/pmax_more_images.json
"""
import json
import os

import httpx
from dotenv import load_dotenv

from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
DEP = "/home/jason/shopify-admin/deploy"
AG = f"customers/{CID}/assetGroups/6770847164"
STATE = f"{DEP}/pmax_more_images.json"
WANT = 4  # 目标附加方图数

state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
state.setdefault("done_products", [])   # 已上传的产品 id
state.setdefault("asset_rns", [])


def save():
    json.dump(state, open(STATE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


cl = ShopifyRest(StoreService().get_client(1)).client

# ---- 1) 找 medical-battery collection ----
col_id = None
for kind in ("custom_collections.json", "smart_collections.json"):
    for cs in cl.request("GET", kind, params={"limit": 250}).get(
            kind.split(".")[0], []):
        if cs.get("handle") == "medical-battery":
            col_id = cs["id"]
            kind_key = kind.split(".")[0]
            break
    if col_id:
        break
if not col_id:
    raise SystemExit("collection medical-battery 未找到")
print(f"collection id: {col_id} ({kind_key})")

# ---- 2) 条码风险产品黑名单 ----
bad = set()
bfile = f"{DEP}/barcode_scan_result.jsonl"
if os.path.exists(bfile):
    for line in open(bfile, encoding="utf-8"):
        try:
            bad.add(json.loads(line).get("product_id"))
        except Exception:
            pass
    print(f"条码风险黑名单: {len(bad)} 个产品")

# ---- 3) 拉产品主图 ----
prods = cl.request(
    "GET", f"collections/{col_id}/products.json",
    params={"limit": 50, "fields": "id,title,images"})["products"]
cands = []
for p in prods:
    if p["id"] in bad or p["id"] in state["done_products"]:
        continue
    src = (p.get("images") or [{}])[0].get("src")
    if src:
        cands.append((p["id"], p["title"], src))
print(f"候选产品图: {len(cands)} (需 {WANT - len(state['done_products'])})")

# ---- 4) 上传为附加方图 ----
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
asvc = client.get_service("AssetService")
gsvc = client.get_service("AssetGroupAssetService")
gas0 = client.get_service("GoogleAdsService")
mime_map = {"image/jpeg": "IMAGE_JPEG", "image/png": "IMAGE_PNG"}

# 孤儿 asset 复用（上次 link 失败但上传成功的）
asset_cache = {}
for row in gas0.search(customer_id=CID, query=(
        "SELECT asset.resource_name, asset.name FROM asset "
        "WHERE asset.name LIKE 'Med SQ %'")):
    asset_cache[row.asset.name] = row.asset.resource_name

for pid, title, src in cands:
    if len(state["done_products"]) >= WANT:
        break
    key = f"Med SQ {pid}"
    if key in asset_cache:
        arn = asset_cache[key]
    else:
        url = src + ("&" if "?" in src else "?") + "width=1200"
        r = httpx.get(url, timeout=60, follow_redirects=True)
        ct = r.headers.get("content-type", "").split(";")[0].strip()
        mime = mime_map.get(ct)
        if r.status_code != 200 or not mime or len(r.content) > 4_500_000:
            print(f"skip {pid}: http={r.status_code} ct={ct} bytes={len(r.content)}")
            continue
        aop = client.get_type("AssetOperation")
        a = aop.create
        a.name = key
        a.type_ = client.enums.AssetTypeEnum.IMAGE
        a.image_asset.data = r.content
        a.image_asset.mime_type = getattr(
            client.enums.MimeTypeEnum, mime)
        try:
            aresp = asvc.mutate_assets(
                customer_id=CID, operations=[aop])
            arn = aresp.results[0].resource_name
        except Exception as e:
            print(f"asset upload fail {pid}: {e}")
            continue
    gop = client.get_type("AssetGroupAssetOperation")
    g = gop.create
    g.asset_group = AG
    g.asset = arn
    g.field_type = (
        client.enums.AssetFieldTypeEnum.SQUARE_MARKETING_IMAGE)
    try:
        gresp = gsvc.mutate_asset_group_assets(
            customer_id=CID, operations=[gop])
        state["asset_rns"].append(gresp.results[0].resource_name)
    except Exception as e:
        print(f"link fail {pid}: {e}")
        continue
    state["done_products"].append(pid)
    save()
    print(f"linked: {title[:50]} ({arn})")

# ---- 5) readback ----
gas = client.get_service("GoogleAdsService")
rows = gas.search(customer_id=CID, query=(
    "SELECT asset_group_asset.asset, asset_group_asset.field_type, "
    "asset_group_asset.status FROM asset_group_asset "
    f"WHERE asset_group_asset.asset_group='{AG}'"))
img = 0
for row in rows:
    ft = row.asset_group_asset.field_type.name
    if "IMAGE" in ft:
        img += 1
        print("live image asset:", ft,
              row.asset_group_asset.status.name)
print(f"=== 资产组图片资产共 {img} 张 ===")
print("(ad_strength 评分有数小时延迟，稍后在 ads.google.com 资产组页查看)")
