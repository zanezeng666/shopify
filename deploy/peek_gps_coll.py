# -*- coding: utf-8 -*-
"""GPS 深挖：collection 发布状态 + RSA 完整 policy topic。"""
import json

colls = json.load(open("/tmp/colls.json"))
if isinstance(colls, list):
    for c in colls:
        if c.get("handle") == "gps-navigator-battery":
            print("collection 字段:", json.dumps(
                {k: c.get(k) for k in
                 ("id", "handle", "title", "published_at",
                  "updated_at", "products_count")},
                ensure_ascii=False, indent=1))
            break
    else:
        print("colls 中无该 handle")
else:
    print("dict 形态:", {k: v for k, v in colls.items()
                         if "gps" in str(k)})
