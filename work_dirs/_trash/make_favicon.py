# -*- coding: utf-8 -*-
"""生成 Estry favicon：512x512 圆角蓝底 + 白色 E + 绿色角标。"""
from PIL import Image, ImageDraw, ImageFont

S = 512
NAVY = (1, 68, 141, 255)
GREEN = (132, 194, 39, 255)
WHITE = (255, 255, 255, 255)

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
# 圆角底
d.rounded_rectangle([8, 8, S - 8, S - 8], radius=96, fill=NAVY)

# 白色 E —— 用 Arial Bold 大字
font = None
for p in [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\ariblk.ttf"]:
    try:
        font = ImageFont.truetype(p, 340)
        break
    except OSError:
        continue
if font is None:
    font = ImageFont.load_default()

bb = d.textbbox((0, 0), "E", font=font)
w, h = bb[2] - bb[0], bb[3] - bb[1]
x = (S - w) / 2 - bb[0]
y = (S - h) / 2 - bb[1] - 18
d.text((x, y), "E", font=font, fill=WHITE)

# 右下绿色小方块点缀（品牌绿）
d.rounded_rectangle([S - 148, S - 148, S - 68, S - 68], radius=22, fill=GREEN)

img.save(r"E:\worksapce\shopify\work_dirs\_trash\favicon-estry.png")
# 同时出 64px 预览确认可辨
img.resize((64, 64), Image.LANCZOS).save(r"E:\worksapce\shopify\work_dirs\_trash\favicon-preview64.png")
print("saved", img.size)
