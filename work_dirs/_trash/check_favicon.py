# -*- coding: utf-8 -*-
"""favicon 结构像素探针。"""
from PIL import Image

img = Image.open(r"E:\worksapce\shopify\work_dirs\_trash\favicon-estry.png").convert("RGBA")
S = img.size[0]
px = img.load()


def near(c, t, tol=28):
    return all(abs(c[i] - t[i]) <= tol for i in range(3))

navy = (1, 68, 141)
green = (132, 194, 39)
white = (255, 255, 255)

navy_n = white_n = green_n = 0
for yy in range(0, S, 4):
    for xx in range(0, S, 4):
        c = px[xx, yy]
        if near(c, navy):
            navy_n += 1
        elif near(c, white):
            white_n += 1
        elif near(c, green):
            green_n += 1
tot = (S // 4) * (S // 4)
print(f"navy={navy_n/tot:.0%} whiteE={white_n/tot:.0%} green={green_n/tot:.0%}")
# E 中心横杠应白、左上角蓝、右下绿块
print("center white:", near(px[S//2, S//2], white))
print("corner navy:", near(px[S//4, S//4], navy))
print("green block:", near(px[S-110, S-110], green))
