# -*- coding: utf-8 -*-
"""读品牌图属性：尺寸/格式/主色/边缘留白，决定 logo 上传形态。"""
import sys
from pathlib import Path

p = Path(r"C:\Users\admin\Documents\Tencent Files\2650949163\nt_qq\nt_data\Pic\2026-11\Ori\96f5bad1d11b0ba10a103bbddbc7bd39.jpg")
print("exists", p.exists(), "size", p.stat().st_size if p.exists() else 0)
if not p.exists():
    sys.exit(1)

import cv2
import numpy as np

img = cv2.imdecode(np.fromfile(str(p), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
if img is None:
    print("decode failed")
    sys.exit(1)
h, w = img.shape[:2]
print(f"dims {w}x{h} channels {img.shape[2] if img.ndim==3 else 1}")

if img.ndim == 3 and img.shape[2] == 3:
    b, g, r = cv2.split(img)
    a = None
else:
    b, g, r, a = cv2.split(img)

rgb = cv2.merge((r, g, b))
if a is not None:
    print("has alpha, opaque ratio", float((a > 0).mean()))

# 四角 20x20 中位色（背景色）
corners = np.concatenate([
    rgb[:20, :20].reshape(-1, 3), rgb[:20, -20:].reshape(-1, 3),
    rgb[-20:, :20].reshape(-1, 3), rgb[-20:, -20:].reshape(-1, 3)])
print("corner bg median RGB", np.median(corners, axis=0).astype(int).tolist())

# 内容 bbox（与背景差异 >25 的区域）
bg = np.median(corners, axis=0)
diff = np.abs(rgb.astype(int) - bg.astype(int)).sum(axis=2)
mask = diff > 60
ys, xs = np.where(mask)
if len(xs):
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    print(f"content bbox x[{x0},{x1}] y[{y0},{y1}] -> {x1-x0+1}x{y1-y0+1}px, aspect {round((x1-x0+1)/(y1-y0+1),2)}")
else:
    print("no distinct content found")

# 全图主色 top5（kmeans 粗分）
small = cv2.resize(rgb, (120, max(1, int(120*h/w)))) if w >= h else cv2.resize(rgb, (max(1, int(120*w/h)), 120))
data = small.reshape(-1, 3).astype(np.float32)
k = 5
_, labels, centers = cv2.kmeans(data, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3, cv2.KMEANS_PP_CENTERS)
counts = np.bincount(labels.flatten(), minlength=k)
order = np.argsort(-counts)
for i in order:
    c = centers[i].astype(int).tolist()
    print(f"color {c} share {round(float(counts[i])/len(labels)*100,1)}%")

# 保存一份内容裁剪版到 _trash 供上传备用
if len(xs):
    pad = 8
    x0p, y0p = max(0, x0 - pad), max(0, y0 - pad)
    x1p, y1p = min(w, x1 + 1 + pad), min(h, y1 + 1 + pad)
    crop = img[y0p:y1p, x0p:x1p]
    out = Path(r"E:\worksapce\shopify\work_dirs\_trash\brand_crop.png")
    ok, buf = cv2.imencode(".png", crop)
    buf.tofile(str(out))
    print("saved crop", out.name, f"{crop.shape[1]}x{crop.shape[0]}")
