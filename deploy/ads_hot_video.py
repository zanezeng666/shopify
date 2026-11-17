# -*- coding: utf-8 -*-
"""热销医疗视频 v2: Hot SQ2 方图 → 10s 轮播 → YouTube → 替换 PMax 挂载。

断点安全: asset 已存在则跳过渲染/上传, 只做挂载。
"""
import json
import os
import time

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG_RN = f"customers/{CID}/assetGroups/6770847164"
MP4 = "/home/jason/shopify-admin/deploy/estry_hot_10s.mp4"
ANAME = "Hot Carousel Video 10s v2"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")
asvc = client.get_service("AssetService")
aga = client.get_service("AssetGroupAssetService")

# ---- 0) 已有 asset 则复用 ----
arn = None
q0 = f"SELECT asset.resource_name FROM asset " \
     f"WHERE asset.name = '{ANAME}'"
for r0 in gas.search(customer_id=CID, query=q0):
    arn = r0.asset.resource_name

if arn:
    print(f"复用已有 asset: {arn}")
else:
    # ---- 1) Shopify 拉热销产品图(pad 1:1) ----
    from io import BytesIO  # noqa: E402

    from PIL import Image, ImageOps  # noqa: E402
    from moviepy.editor import ImageSequenceClip  # noqa: E402
    from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
    from shopify_admin.services.stores.service import StoreService  # noqa: E402

    PICKS = [4626167922788, 4644569940068, 4638407622756, 7840406470900]
    cl = ShopifyRest(StoreService().get_client(1)).client
    ids = ",".join(str(x) for x in PICKS)
    r = cl.request("GET", "products.json",
                   params={"ids": ids, "fields": "id,title,images"})
    prods = {p["id"]: p for p in r.get("products", [])}
    imgs = []
    for pid in PICKS:
        p = prods.get(pid)
        if not p or not p.get("images"):
            raise SystemExit(f"!! P{pid} 无图, 中止")
        url = p["images"][0]["src"]
        url += ("&" if "?" in url else "?") + "width=1200"
        d = httpx.get(url, timeout=60, follow_redirects=True).content
        img = Image.open(BytesIO(d)).convert("RGB")
        img = ImageOps.contain(img, (1200, 1200))
        canvas = Image.new("RGB", (1200, 1200), (255, 255, 255))
        canvas.paste(img, ((1200 - img.width) // 2,
                           (1200 - img.height) // 2))
        fn = f"/tmp/hot_{len(imgs)}.jpg"
        canvas.save(fn, "JPEG", quality=92)
        imgs.append(fn)
        print(f"  图 {p['title'][:44]}")
    if len(imgs) != 4:
        raise SystemExit(f"图不足4张({len(imgs)}), 中止")

    # ---- 2) 渲染 10s 轮播 ----
    clip = ImageSequenceClip(imgs, fps=0.4)
    clip.write_videofile(MP4, fps=30, logger=None)
    print(f"渲染 OK -> {MP4}")

    # ---- 3) YouTube 上传 ----
    r = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    access = r.json()["access_token"]
    meta = {"snippet": {
        "title": "Estry Medical Device Batteries - Hot Models",
        "description": "Replacement batteries for Welch Allyn, Nuflo, "
                       "Rainin and Philips medical devices. Fast US "
                       "shipping, 1-year warranty. "
                       "https://estrybattery.com",
        "categoryId": "28"},
        "status": {"privacyStatus": "unlisted",
                   "selfDeclaredMadeForKids": False}}
    boundary = "estryhot9d2f"
    body = (f"--{boundary}\r\nContent-Type: application/json; "
            f"charset=UTF-8\r\n\r\n" + json.dumps(meta)
            + f"\r\n--{boundary}\r\nContent-Type: video/mp4\r\n\r\n"
            ).encode() + open(MP4, "rb").read() \
            + f"\r\n--{boundary}--\r\n".encode()
    up = httpx.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=multipart&part=snippet,status",
        headers={"Authorization": f"Bearer {access}",
                 "Content-Type":
                     f"multipart/related; boundary={boundary}"},
        content=body, timeout=300)
    up.raise_for_status()
    vid = up.json()["id"]
    print(f"YouTube OK: https://youtu.be/{vid}")

    # ---- 4) 建 asset(等待 YouTube 传播, 重试3次) ----
    aop = client.get_type("AssetOperation")
    a = aop.create
    a.name = ANAME
    a.type_ = client.enums.AssetTypeEnum.YOUTUBE_VIDEO
    a.youtube_video_asset.youtube_video_id = vid
    for attempt in range(3):
        try:
            arn = asvc.mutate_assets(
                customer_id=CID, operations=[aop]
            ).results[0].resource_name
            print(f"asset OK: {arn}")
            break
        except Exception as e:  # noqa: BLE001
            s = str(e)
            i = s.find("errors {")
            print(f"asset 尝试{attempt+1}失败: "
                  f"{s[i:i+300] if i >= 0 else s[:300]}")
            if attempt == 2:
                raise SystemExit(1)
            time.sleep(30)

# ---- 5) 挂新 + 摘旧 VIDEO ----
ops = []
gop = client.get_type("AssetGroupAssetOperation")
g = gop.create
g.asset_group = AG_RN
g.asset = arn
g.field_type = "YOUTUBE_VIDEO"
g.status = "ENABLED"
ops.append(gop)
q2 = ("SELECT asset_group_asset.resource_name "
      "FROM asset_group_asset "
      f"WHERE asset_group_asset.asset_group = '{AG_RN}' "
      "AND asset_group_asset.field_type = 'YOUTUBE_VIDEO'")
olds = [r.asset_group_asset.resource_name
        for r in gas.search(customer_id=CID, query=q2)]
print(f"旧视频挂载: {olds}")
for o in olds:
    rop = client.get_type("AssetGroupAssetOperation")
    rop.remove = o
    ops.append(rop)
try:
    aga.mutate_asset_group_assets(customer_id=CID, operations=ops)
    print("挂载替换 OK")
except Exception as e:  # noqa: BLE001
    s = str(e)
    i = s.find("errors {")
    print(f"挂载失败:\n{s[i:i+600] if i >= 0 else s[:600]}")
    raise SystemExit(1)

# ---- 6) readback ----
q3 = ("SELECT asset_group_asset.field_type, asset_group_asset.status, "
      "asset.name FROM asset_group_asset "
      f"WHERE asset_group_asset.asset_group = '{AG_RN}' "
      "AND asset_group_asset.field_type = 'YOUTUBE_VIDEO'")
for r in gas.search(customer_id=CID, query=q3):
    print(f"  live VIDEO: [{r.asset_group_asset.status.name}] "
          f"{r.asset.name}")
q4 = ("SELECT asset_group.ad_strength FROM asset_group "
      f"WHERE asset_group.resource_name = '{AG_RN}'")
for r in gas.search(customer_id=CID, query=q4):
    print(f"  ad_strength: {r.asset_group.ad_strength.name}")
