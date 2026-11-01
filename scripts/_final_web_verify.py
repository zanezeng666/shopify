# -*- coding: utf-8 -*-
"""终验：新 draft vs 老 active 网页维度（body_html 结构 + options）对比。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)

OLD = 7122951831719   # Amarey 老品
NEW = 15476051214580  # Goovi 新 draft


def skeleton(pid):
    p = client.request("GET", f"products/{pid}.json",
                       params={"fields": "handle,status,options,body_html,variants"})["product"]
    b = p.get("body_html") or ""
    # 结构骨架：标签序列（忽略文本内容与空白）
    import re
    tags = re.findall(r"<(/?\w+)[^>]*>", b)
    tags = [t for t in tags if t not in ("/br", "/b", "/li", "/ul")]
    v = (p.get("variants") or [{}])[0]
    return {
        "status": p.get("status"),
        "options": [(o.get("name"), o.get("values")) for o in p.get("options") or []],
        "option1": v.get("option1"),
        "body_head": b[:28],
        "has_spec_table": "Battery Specifications" in b and b.count("<table") == 2,
        "spec_rows": len(re.findall(r"<tr>", b)),
        "tag_seq": tags,
    }


old = skeleton(OLD)
new = skeleton(NEW)
print("老品:", {k: old[k] for k in ("status", "options", "option1", "body_head", "has_spec_table", "spec_rows")})
print("新品:", {k: new[k] for k in ("status", "options", "option1", "body_head", "has_spec_table", "spec_rows")})
print("标签序列一致:", old["tag_seq"] == new["tag_seq"])
if old["tag_seq"] != new["tag_seq"]:
    print("老:", old["tag_seq"])
    print("新:", new["tag_seq"])
