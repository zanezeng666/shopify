# -*- coding: utf-8 -*-
"""用真实产品图合成 PMax 营销素材：横版 1200x628 x2 + 竖版 960x1200 x2。"""
from PIL import Image, ImageDraw, ImageFont

A = "e:/worksapce/shopify/deploy/assets"
FB = "C:/Windows/Fonts/arialbd.ttf"
FR = "C:/Windows/Fonts/arial.ttf"
BLUE = (26, 82, 158)
DARK = (23, 43, 77)
GREY = (90, 105, 130)


def load(n):
    return Image.open(f"{A}/prod_{n}.jpg").convert("RGB")


def fit(im, w, h):
    """cover 裁剪缩放。"""
    r = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1))
    x = (im.width - w) // 2
    y = (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def card(im, w, h):
    """产品图贴白卡片（含边框）。"""
    pad = 14
    inner = fit(im, w - 2 * pad, h - 2 * pad)
    c = Image.new("RGB", (w, h), (255, 255, 255))
    c.paste(inner, (pad, pad))
    d = ImageDraw.Draw(c)
    d.rectangle([0, 0, w - 1, h - 1], outline=(225, 230, 240), width=2)
    return c


# ---------- 横版 A：左文右图 ----------
w, h = 1200, 628
im = Image.new("RGB", (w, h))
d = ImageDraw.Draw(im)
for y_ in range(h):  # 浅蓝渐变底
    t = y_ / h
    d.line([(0, y_), (w, y_)],
           fill=(int(235 - 20 * t), int(243 - 15 * t), 252))
im.paste(card(load(2), 320, 420), (w - 700, 104))
im.paste(card(load(3), 320, 420), (w - 350, 104))
d = ImageDraw.Draw(im)
d.text((64, 120), "Exact-Fit Medical", font=ImageFont.truetype(FB, 62),
       fill=DARK)
d.text((64, 196), "Device Batteries", font=ImageFont.truetype(FB, 62),
       fill=BLUE)
d.text((64, 300), "200+ OEM Models • In Stock",
       font=ImageFont.truetype(FR, 34), fill=GREY)
d.text((64, 352), "Fast US Shipping", font=ImageFont.truetype(FR, 34),
       fill=GREY)
d.rounded_rectangle([64, 440, 470, 510], 35, fill=BLUE)
d.text((104, 456), "1-Year Warranty", font=ImageFont.truetype(FB, 36),
       fill=(255, 255, 255))
im.save(f"{A}/wide_a_1200x628.jpg", quality=92)

# ---------- 横版 B：三图横排 ----------
im = Image.new("RGB", (w, h), (255, 255, 255))
d = ImageDraw.Draw(im)
d.rectangle([0, 0, w, 118], fill=BLUE)
d.text((60, 34), "Replacement Batteries for Defibrillators, Monitors"
       " & Ultrasound", font=ImageFont.truetype(FB, 38), fill=(255, 255, 255))
for i, pn in enumerate((4, 7, 9)):
    im.paste(card(load(pn), 330, 400), (60 + i * 360, 168))
d.text((60, 590), "Exact fit for 200+ device models — ships from US stock",
       font=ImageFont.truetype(FR, 28), fill=GREY)
im.save(f"{A}/wide_b_1200x628.jpg", quality=92)

# ---------- 竖版 A：上图下文 ----------
w, h = 960, 1200
im = Image.new("RGB", (w, h))
d = ImageDraw.Draw(im)
im.paste(card(load(0), 760, 640), (100, 70))
d.text((80, 770), "Exact-Fit", font=ImageFont.truetype(FB, 78), fill=DARK)
d.text((80, 860), "Medical Batteries", font=ImageFont.truetype(FB, 78),
       fill=BLUE)
d.text((80, 980), "200+ OEM models • In stock", font=ImageFont.truetype(
    FR, 40), fill=GREY)
d.text((80, 1040), "Fast US shipping", font=ImageFont.truetype(FR, 40),
       fill=GREY)
d.rounded_rectangle([80, 1096, 560, 1168], 36, fill=BLUE)
d.text((130, 1112), "1-Year Warranty", font=ImageFont.truetype(FB, 38),
       fill=(255, 255, 255))
im.save(f"{A}/tall_a_960x1200.jpg", quality=92)

# ---------- 竖版 B：2x2 网格 ----------
im = Image.new("RGB", (w, h), (246, 249, 253))
d = ImageDraw.Draw(im)
d.rectangle([0, 0, w, 150], fill=DARK)
d.text((70, 44), "Batteries for 200+ Medical Devices",
       font=ImageFont.truetype(FB, 44), fill=(255, 255, 255))
for i, (px, py) in enumerate(((60, 190), (500, 190),
                              (60, 620), (500, 620))):
    im.paste(card(load((5, 6, 8, 1)[i]), 400, 400), (px, py))
d.text((70, 1070), "OEM-fit • In stock • Ships from US",
       font=ImageFont.truetype(FR, 38), fill=GREY)
d.rounded_rectangle([70, 1120, 550, 1190], 35, fill=BLUE)
d.text((140, 1135), "Shop EstryBattery", font=ImageFont.truetype(FB, 36),
       fill=(255, 255, 255))
im.save(f"{A}/tall_b_960x1200.jpg", quality=92)

import os
for f in ("wide_a_1200x628.jpg", "wide_b_1200x628.jpg",
          "tall_a_960x1200.jpg", "tall_b_960x1200.jpg", "logo-1200.png"):
    p = f"{A}/{f}"
    print(f, Image.open(p).size, f"{os.path.getsize(p)//1024}KB")
