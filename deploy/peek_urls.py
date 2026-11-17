# -*- coding: utf-8 -*-
"""核对 plans 落地页 handle vs 实际 collections 差集。"""
import json

plans = json.load(open("/tmp/allcat_plans.json"))
colls = json.load(open("/tmp/colls.json"))
# colls.json 结构兼容两种：[{handle,...}] 或 {handle: n}
if isinstance(colls, dict):
    have = set(colls)
else:
    have = {c.get("handle") for c in colls}
print("collections 总数:", len(have))
missing, ok = [], []
for p in plans:
    h = p["url"].rsplit("/", 1)[-1]
    (ok if h in have else missing).append((p["campaign"], h))
print(f"\n== 缺失落地页 {len(missing)} 个:")
for name, h in missing:
    print(" ", name, "->", h)
print(f"\n== 正常 {len(ok)} 个")
# 顺带找 gps 相关 handle
print("\ngps 相关 handle:",
      sorted(x for x in have if x and "gps" in x.lower()))
print("navigator 相关 handle:",
      sorted(x for x in have if x and "navigator" in x.lower()))
