# -*- coding: utf-8 -*-
"""PMax 效力修复 v3：竖版图（带name）+ campaign层 Brand Guidelines（logo+商家名）。"""
import io
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.protobuf import field_mask_pb2

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG_RN = f"customers/{CID}/assetGroups/6770847164"
CAMP_RN = f"customers/{CID}/campaigns/24441391608"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
asset_svc = client.get_service("AssetService")
aga_svc = client.get_service("AssetGroupAssetService")
ca_svc = client.get_service("CampaignAssetService")
camp_svc = client.get_service("CampaignService")
E = client.enums


def full_err(e):
    try:
        return " | ".join(er.message[:200] for er in e.failure.errors)
    except AttributeError:
        return str(e)[:250]


def new_asset(setter) -> str:
    op = client.get_type("AssetOperation")
    setter(op.create)
    r = asset_svc.mutate_assets(customer_id=CID, operations=[op])
    return r.results[0].resource_name


def aga_link(asset_rn, field_type):
    op = client.get_type("AssetGroupAssetOperation")
    op.create.asset_group = AG_RN
    op.create.asset = asset_rn
    op.create.field_type = field_type
    op.create.status = "ENABLED"
    try:
        aga_svc.mutate_asset_group_assets(customer_id=CID, operations=[op])
        print("    挂载 OK")
    except Exception as e:  # noqa: BLE001
        print(f"    [挂载失败] {full_err(e)}")


def camp_link(asset_rn, field_type, label):
    op = client.get_type("CampaignAssetOperation")
    op.create.campaign = CAMP_RN
    op.create.asset = asset_rn
    op.create.field_type = field_type
    try:
        ca_svc.mutate_campaign_assets(customer_id=CID, operations=[op])
        print(f"  [OK] {label} campaign 层挂载")
    except Exception as e:  # noqa: BLE001
        print(f"  [失败:{label}] {full_err(e)}")


# ---------- B: 竖版图（带 name） ----------
print("=== B. 竖版图 ===")
try:
    from PIL import Image
    import httpx
    q = ("SELECT asset_group_asset.asset FROM asset_group_asset "
         f"WHERE asset_group_asset.asset_group = '{AG_RN}' "
         "AND asset_group_asset.field_type IN "
         "('SQUARE_MARKETING_IMAGE','MARKETING_IMAGE')")
    rns = [str(r.asset_group_asset.asset)
           for r in gas.search(customer_id=CID, query=q)]
    urls, name_of = {}, {}
    for i in range(0, len(rns), 90):
        chunk = ", ".join(f"'{x}'" for x in rns[i:i + 90])
        qimg = ("SELECT asset.resource_name, asset.name, "
                "asset.image_asset.full_size.url FROM asset "
                f"WHERE asset.resource_name IN ({chunk})")
        for r in gas.search(customer_id=CID, query=qimg):
            if r.asset.image_asset.full_size.url:
                name_of[r.asset.name or ""] = str(r.asset.resource_name)
                urls[r.asset.name or ""] = r.asset.image_asset.full_size.url
    brand_url = next((u for n, u in urls.items() if "Estry Square" in n), None)
    prod_url = next((u for n, u in urls.items() if "7840406470900" in n), None)

    def upload_img(img, label, name):
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "JPEG", quality=88)
        print(f"  {label} {img.size[0]}x{img.size[1]} "
              f"({len(buf.getvalue())//1024}KB)")

        def setter(a, buf=buf, name=name):
            a.name = name
            a.image_asset.data = buf.getvalue()
            a.image_asset.mime_type = "IMAGE_JPEG"
        try:
            rn = new_asset(setter)
            aga_link(rn, E.AssetFieldTypeEnum.PORTRAIT_MARKETING_IMAGE)
        except Exception as e:  # noqa: BLE001
            print(f"    [创建失败] {full_err(e)}")

    if brand_url:
        im = Image.open(io.BytesIO(httpx.get(brand_url, timeout=60).content))
        w, h = im.size
        cw = int(h * 4 / 5)
        if w >= cw:
            x0 = (w - cw) // 2
            upload_img(im.crop((x0, 0, x0 + cw, h)), "品牌4:5", "Estry Portrait 4x5")
        cw9 = int(h * 9 / 16)
        if w >= cw9:
            x0 = (w - cw9) // 2
            upload_img(im.crop((x0, 0, x0 + cw9, h)).resize((720, 1280)),
                       "品牌9:16", "Estry Portrait 9x16")
    if prod_url:
        im = Image.open(io.BytesIO(httpx.get(prod_url, timeout=60).content))
        w, h = im.size
        cw9 = int(h * 9 / 16)
        if w >= cw9:
            x0 = (w - cw9) // 2
            upload_img(im.crop((x0, 0, x0 + cw9, h)).resize((720, 1280)),
                       "产品9:16", "Estry Med Portrait 9x16")
except ImportError:
    print("  [跳过] 无 PIL")

# ---------- C: campaign 层 Brand Guidelines ----------
print("\n=== C. 商家名 + Logo（campaign 层） ===")
# C1: BUSINESS_NAME（text asset "Estry" 挂 campaign）
try:
    rn = new_asset(lambda a: setattr(a.text_asset, "text", "Estry"))
    camp_link(rn, E.AssetFieldTypeEnum.BUSINESS_NAME, "商家名 Estry")
except Exception as e:  # noqa: BLE001
    print(f"  [失败:商家名创建] {full_err(e)}")

# C2: LOGO（复用 1200x1200 品牌方图，压到 <=120KB 再建新 asset 保险）
logo_rn = next((rn for n, rn in name_of.items() if "Estry Square" in n), None)
if logo_rn:
    camp_link(logo_rn, E.AssetFieldTypeEnum.LOGO, "Logo(复用方图)")
else:
    print("  [未找到品牌方图]")

# ---------- D: readback ----------
print("\n=== D. Readback ===")
q5 = ("SELECT asset_group_asset.field_type, asset_group_asset.status "
      "FROM asset_group_asset "
      f"WHERE asset_group_asset.asset_group = '{AG_RN}'")
from collections import Counter  # noqa: E402
cnt = Counter()
for r in gas.search(customer_id=CID, query=q5):
    cnt[f"{r.asset_group_asset.field_type.name}/"
        f"{r.asset_group_asset.status.name}"] += 1
for k in sorted(cnt):
    print(f"  AG[{k}]: {cnt[k]}")
q6 = ("SELECT campaign_asset.field_type, campaign_asset.status "
      "FROM campaign_asset "
      f"WHERE campaign_asset.campaign = '{CAMP_RN}'")
for r in gas.search(customer_id=CID, query=q6):
    print(f"  Camp[{r.campaign_asset.field_type.name}/"
          f"{r.campaign_asset.status.name}]")
q4 = ("SELECT asset_group.ad_strength FROM asset_group "
      f"WHERE asset_group.resource_name = '{AG_RN}'")
for r in gas.search(customer_id=CID, query=q4):
    print(f"  ad_strength: {r.asset_group.ad_strength.name}")
