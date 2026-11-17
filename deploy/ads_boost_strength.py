# -*- coding: utf-8 -*-
"""PMax 效力提升 v2：补齐标题/长标题/描述/CTA + 生成竖版图 + Logo。"""
import io
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG_RN = f"customers/{CID}/assetGroups/6770847164"

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
E = client.enums


def full_err(e):
    parts = []
    try:
        for er in e.failure.errors:  # GoogleAdsException
            parts.append(f"{er.error_code}.{er.message[:200]}")
    except AttributeError:
        try:
            parts.append(e.details())
        except Exception:  # noqa: BLE001
            parts.append(str(e)[:300])
    return " | ".join(parts) or str(e)[:300]


def new_asset(setter) -> str:
    op = client.get_type("AssetOperation")
    setter(op.create)  # 直接在 create 消息上设字段
    r = asset_svc.mutate_assets(customer_id=CID, operations=[op])
    return r.results[0].resource_name


def link(asset_rn, field_type):
    op = client.get_type("AssetGroupAssetOperation")
    op.create.asset_group = AG_RN
    op.create.asset = asset_rn
    op.create.field_type = field_type
    op.create.status = "ENABLED"
    try:
        aga_svc.mutate_asset_group_assets(customer_id=CID, operations=[op])
        return True
    except Exception as e:  # noqa: BLE001
        print(f"    [挂载失败] {full_err(e)}")
        return False


def create_and_link(setter, field_type, label):
    try:
        rn = new_asset(setter)
    except Exception as e:  # noqa: BLE001
        print(f"    [创建失败:{label}] {full_err(e)}")
        return
    ok = link(rn, field_type)
    print(f"  [OK] {label} -> {'挂载' if ok else '未挂'}")


# ---------- A: 文本素材（按缺口幂等补齐） ----------
q_cnt = ("SELECT asset_group_asset.field_type "
         f"FROM asset_group_asset WHERE asset_group_asset.asset_group = '{AG_RN}' "
         "AND asset_group_asset.status = 'ENABLED'")
from collections import Counter  # noqa: E402
have = Counter(r.asset_group_asset.field_type.name
               for r in gas.search(customer_id=CID, query=q_cnt))
print(f"现有: 标题{have['HEADLINE']}/15 长标题{have['LONG_HEADLINE']}/5 "
      f"描述{have['DESCRIPTION']}/5")

print("=== A1. 标题 ===")
HEADLINES = ("Defib Battery", "Monitor Battery", "OEM-Fit, In Stock",
             "Exact-Fit Medical Cells", "Medical Battery Experts",
             "Replacement Medical Batteries", "Buy Medical Batteries Online")
for t in HEADLINES:
    if have["HEADLINE"] >= 15:
        print("  [跳过] 已满 15")
        break
    create_and_link(lambda a, t=t: setattr(a.text_asset, "text", t),
                    E.AssetFieldTypeEnum.HEADLINE, f"标题({len(t)}字) {t}")
    have["HEADLINE"] += 1

print("=== A2. 长标题 ===")
for t in ("OEM-Fit Batteries for Patient Monitors, Defibs, Ventilators & Ultrasound. Ships From US.",
          "Exact-Fit Medical Batteries for 200+ Device Models. In Stock, Fast US Delivery."):
    if have["LONG_HEADLINE"] >= 5:
        print("  [跳过] 已满 5")
        break
    create_and_link(lambda a, t=t: setattr(a.text_asset, "text", t),
                    E.AssetFieldTypeEnum.LONG_HEADLINE, f"长标题({len(t)}字)")
    have["LONG_HEADLINE"] += 1

print("=== A3. 描述 +2 ===")
for t in ("Precise-fit replacement cells for monitors, defibs & vents. US stock, 1-year warranty.",
          "High-capacity medical batteries, exact fit for your device. Order today, ships fast."):
    if have["DESCRIPTION"] >= 5:
        print("  [跳过] 已满 5")
        break
    create_and_link(lambda a, t=t: setattr(a.text_asset, "text", t),
                    E.AssetFieldTypeEnum.DESCRIPTION, f"描述({len(t)}字)")
    have["DESCRIPTION"] += 1

print("=== A4. CTA ===")
try:
    client.get_type("Asset").call_to_action_asset  # 探字段
    create_and_link(
        lambda a: setattr(a.call_to_action_asset, "call_to_action", "SHOP_NOW"),
        E.AssetFieldTypeEnum.CALL_TO_ACTION_ASSET, "SHOP_NOW")
except AttributeError:
    print("  [跳过] v26 Asset 无 call_to_action_asset 字段")

# ---------- B: 竖版图 ----------
print("=== B. 竖版图 ===")
if have["PORTRAIT_MARKETING_IMAGE"] >= 3:
    print("  [跳过] 竖版图已有")
else:
    try:
        from PIL import Image
        import httpx
        q = ("SELECT asset_group_asset.asset FROM asset_group_asset "
             f"WHERE asset_group_asset.asset_group = '{AG_RN}' "
             "AND asset_group_asset.field_type IN "
             "('SQUARE_MARKETING_IMAGE','MARKETING_IMAGE')")
        rns = [str(r.asset_group_asset.asset)
               for r in gas.search(customer_id=CID, query=q)]
        urls = {}
        for i in range(0, len(rns), 90):
            chunk = ", ".join(f"'{x}'" for x in rns[i:i + 90])
            qimg = ("SELECT asset.resource_name, asset.name, "
                    "asset.image_asset.full_size.url FROM asset "
                    f"WHERE asset.resource_name IN ({chunk})")
            for r in gas.search(customer_id=CID, query=qimg):
                if r.asset.image_asset.full_size.url:
                    urls[r.asset.name or ""] = r.asset.image_asset.full_size.url
        brand_url = next((u for n, u in urls.items() if "Estry Square" in n), None)
        prod_url = next((u for n, u in urls.items() if "7840406470900" in n), None)
        print(f"  品牌图: {'有' if brand_url else '无'} | "
              f"产品图: {'有' if prod_url else '无'}")

        def upload_img(img, label):
            buf = io.BytesIO()
            img.convert("RGB").save(buf, "JPEG", quality=90)

            def setter(a, buf=buf):
                a.image_asset.data = buf.getvalue()
                a.image_asset.mime_type = "IMAGE_JPEG"
            create_and_link(setter,
                            E.AssetFieldTypeEnum.PORTRAIT_MARKETING_IMAGE,
                            f"{label} {img.size[0]}x{img.size[1]}")

        if brand_url:
            im = Image.open(io.BytesIO(httpx.get(brand_url, timeout=60).content))
            w, h = im.size
            cw = int(h * 4 / 5)
            if w >= cw:
                x0 = (w - cw) // 2
                upload_img(im.crop((x0, 0, x0 + cw, h)), "品牌4:5")
            cw9 = int(h * 9 / 16)
            if w >= cw9:
                x0 = (w - cw9) // 2
                upload_img(im.crop((x0, 0, x0 + cw9, h)).resize((720, 1280)),
                           "品牌9:16")
        if prod_url:
            im = Image.open(io.BytesIO(httpx.get(prod_url, timeout=60).content))
            w, h = im.size
            cw9 = int(h * 9 / 16)
            if w >= cw9:
                x0 = (w - cw9) // 2
                upload_img(im.crop((x0, 0, x0 + cw9, h)).resize((720, 1280)),
                           "产品9:16")
    except ImportError:
        print("  [跳过] 无 PIL")

# ---------- C: Logo ----------
print("=== C. Logo 复用 ===")
q2 = ("SELECT asset_group_asset.asset FROM asset_group_asset "
      f"WHERE asset_group_asset.asset_group = '{AG_RN}' "
      "AND asset_group_asset.field_type = 'SQUARE_MARKETING_IMAGE'")
sq = [str(r.asset_group_asset.asset) for r in gas.search(customer_id=CID, query=q2)]
if sq:
    q3 = ("SELECT asset.resource_name, asset.name FROM asset WHERE "
          f"asset.resource_name IN ({', '.join(chr(39)+x+chr(39) for x in sq)})")
    logo_rn = next((str(r.asset.resource_name)
                    for r in gas.search(customer_id=CID, query=q3)
                    if "Estry Square" in (r.asset.name or "")), None)
    if logo_rn:
        print("  [OK] Logo 挂载" if link(logo_rn, E.AssetFieldTypeEnum.LOGO)
              else "  Logo 挂载失败")

# ---------- D: readback ----------
print("\n=== D. Readback ===")
q5 = ("SELECT asset_group_asset.field_type, asset_group_asset.status "
      "FROM asset_group_asset "
      f"WHERE asset_group_asset.asset_group = '{AG_RN}'")
from collections import Counter  # noqa: E402
cnt = Counter()
for r in gas.search(customer_id=CID, query=q5):
    cnt[f"{r.asset_group_asset.field_type.name}/{r.asset_group_asset.status.name}"] += 1
for k in sorted(cnt):
    print(f"  {k}: {cnt[k]}")
q4 = ("SELECT asset_group.ad_strength FROM asset_group "
      f"WHERE asset_group.resource_name = '{AG_RN}'")
for r in gas.search(customer_id=CID, query=q4):
    print(f"  ad_strength: {r.asset_group.ad_strength.name}（评分重算滞后，几小时后复查）")
