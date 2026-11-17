# -*- coding: utf-8 -*-
"""PMax 产品轮播视频：PIL 渲染 300 帧(10s/30fps/1280x720) -> H.264 mp4 -> 上传挂载。"""
import io
import os
import subprocess
import sys

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG_RN = f"customers/{CID}/assetGroups/6770847164"
W, H, FPS, TOTAL = 1280, 720, 30, 300
SEG = 60          # 每段 2s
XFADE = 12        # crossfade 0.4s
NAVY = (27, 42, 65)     # #1B2A41 品牌深蓝
GREEN = (0, 166, 81)    # #00A651 能量绿
WHITE = (245, 248, 252)
GREY = (168, 180, 196)
BOLD = "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/dejavu/DejaVuSans.ttf"
OUT = "/home/jason/shopify-admin/deploy/estry_carousel_10s.mp4"

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
import httpx  # noqa: E402

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")


def fetch_images():
    """下载 4 张产品方图，按 SKU 序。"""
    q = ("SELECT asset_group_asset.asset FROM asset_group_asset "
         f"WHERE asset_group_asset.asset_group = '{AG_RN}' "
         "AND asset_group_asset.field_type = 'SQUARE_MARKETING_IMAGE'")
    rns = [str(r.asset_group_asset.asset)
           for r in gas.search(customer_id=CID, query=q)]
    named = {}
    for i in range(0, len(rns), 90):
        chunk = ", ".join(f"'{x}'" for x in rns[i:i + 90])
        qi = ("SELECT asset.resource_name, asset.name, "
              "asset.image_asset.full_size.url FROM asset "
              f"WHERE asset.resource_name IN ({chunk})")
        for r in gas.search(customer_id=CID, query=qi):
            if r.asset.image_asset.full_size.url:
                named[r.asset.name or ""] = r.asset.image_asset.full_size.url
    imgs = []
    for sku in sorted(k for k in named if "Med SQ" in k):
        raw = httpx.get(named[sku], timeout=60).content
        imgs.append(Image.open(io.BytesIO(raw)).convert("RGB"))
        print(f"  产品图 {sku}: {imgs[-1].size}")
    if len(imgs) < 4:
        sys.exit(f"产品图不足 4 张({len(imgs)})")
    return imgs


F_CACHE = {}


def font(path, size):
    key = (path, size)
    if key not in F_CACHE:
        F_CACHE[key] = ImageFont.truetype(path, size)
    return F_CACHE[key]


def fit_text(draw, text, bold, max_w, start):
    """字号自适应缩小直到 <=max_w。"""
    s = start
    while s > 20 and draw.textlength(text, font=font(BOLD if bold else REG, s)) > max_w:
        s -= 2
    return font(BOLD if bold else REG, s)


def render_segment(idx, prog, imgs):
    """idx 0=品牌帧 1-4=产品帧；prog 0..1 段内进度。"""
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    if idx == 0:
        f = fit_text(d, "ESTRY", True, 900, 150)
        d.text((W // 2, 300), "ESTRY", font=f, fill=WHITE, anchor="mm")
        d.rounded_rectangle([W // 2 - 120, 380, W // 2 + 120, 392], 6, fill=GREEN)
        d.text((W // 2, 452), "Medical Device Batteries", font=font(REG, 44),
               fill=GREY, anchor="mm")
    else:
        img = imgs[(idx - 1) % 4]
        # Ken Burns: 1.00 -> 1.07 中心放大
        zoom = 1.0 + 0.07 * prog
        iw, ih = img.size
        cw, ch = int(iw / zoom), int(ih / zoom)
        x0, y0 = (iw - cw) // 2, (ih - ch) // 2
        card = img.crop((x0, y0, x0 + cw, y0 + ch)).resize((600, 600), Image.LANCZOS)
        d.rounded_rectangle([72, 60, 708, 696], 22, fill=(255, 255, 255))
        im.paste(card, (90, 78))
        tx, max_w = 764, 470
        title = ["Exact-Fit OEM Batteries", "200+ Device Models",
                 "Fast US Shipping", "1-Year Warranty"][idx - 1]
        sub = ["Precise fit for your device",
               "Monitors / Defibs / Ventilators",
               "In stock, ships from US",
               "Buy with confidence"][idx - 1]
        f = fit_text(d, title, True, max_w, 54)
        d.text((tx, 230), title, font=f, fill=WHITE, anchor="lm")
        d.rounded_rectangle([tx, 278, tx + 64, 286], 4, fill=GREEN)
        d.text((tx, 330), sub, font=font(REG, 30), fill=GREY, anchor="lm")
    d.text((76, 656), "ESTRY", font=font(BOLD, 30), fill=WHITE, anchor="lm")
    d.ellipse([158, 648, 168, 658], fill=GREEN)
    d.text((W - 64, 656), "estrybattery.com", font=font(REG, 24),
           fill=GREY, anchor="rm")
    return im


def build(imgs):
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [exe, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for f in range(TOTAL):
        idx = min(f // SEG, 4)
        prog = (f % SEG) / SEG
        frame = render_segment(idx, prog, imgs)
        if f < 9:                       # 首段品牌色淡入
            frame = Image.blend(Image.new("RGB", (W, H), NAVY), frame, f / 9)
        elif f >= TOTAL - 9:            # 末段淡出
            frame = Image.blend(frame, Image.new("RGB", (W, H), NAVY),
                                (f - (TOTAL - 9)) / 9)
        elif idx < 4 and f % SEG >= SEG - XFADE:   # 段间 crossfade
            a = (f % SEG - (SEG - XFADE)) / XFADE
            frame = Image.blend(frame, render_segment(idx + 1, 0, imgs), a)
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    p.wait()
    print(f"mp4 完成: {OUT} {os.path.getsize(OUT)//1024}KB rc={p.returncode}")


def upload():
    fields = client.get_type("Asset").video_asset._pb.DESCRIPTOR.fields_by_name
    data_field = "data" if "data" in fields else "file"
    print(f"VideoAsset 字段: {list(fields)} 用 {data_field}")

    def setter(a):
        a.name = "Estry Product Carousel 10s"
        with open(OUT, "rb") as fh:
            setattr(a.video_asset, data_field, fh.read())
    asset_svc = client.get_service("AssetService")
    op = client.get_type("AssetOperation")
    setter(op.create)
    r = asset_svc.mutate_assets(customer_id=CID, operations=[op])
    rn = r.results[0].resource_name
    print(f"  视频素材创建: {rn}")

    aga = client.get_service("AssetGroupAssetService")
    op2 = client.get_type("AssetGroupAssetOperation")
    op2.create.asset_group = AG_RN
    op2.create.asset = rn
    op2.create.field_type = "VIDEO"
    op2.create.status = "ENABLED"
    aga.mutate_asset_group_assets(customer_id=CID, operations=[op2])
    print("  挂载 VIDEO OK")

    q = ("SELECT asset_group_asset.field_type, asset_group_asset.status "
         "FROM asset_group_asset "
         f"WHERE asset_group_asset.asset_group = '{AG_RN}'")
    from collections import Counter
    cnt = Counter(f"{r.asset_group_asset.field_type.name}/"
                  f"{r.asset_group_asset.status.name}"
                  for r in gas.search(customer_id=CID, query=q))
    print("  Readback:", dict(cnt))
    q2 = ("SELECT asset_group.ad_strength FROM asset_group "
          f"WHERE asset_group.resource_name = '{AG_RN}'")
    for r in gas.search(customer_id=CID, query=q2):
        print(f"  ad_strength: {r.asset_group.ad_strength.name}")


if __name__ == "__main__":
    print("=== 1. 拉产品图 ===")
    images = fetch_images()
    print("=== 2. 合成视频 ===")
    build(images)
    print("=== 3. 上传挂载 ===")
    try:
        upload()
    except Exception as e:  # noqa: BLE001
        try:
            print("上传失败:", e.failure.errors[0].message[:300])
        except AttributeError:
            print("上传失败:", str(e)[:300])
