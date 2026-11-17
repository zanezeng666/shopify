# -*- coding: utf-8 -*-
"""拉 wholesale page body 看询盘表单结构 + 索引里真实产品 handle。"""
import json
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

rest = ShopifyRest(StoreService().get_client(1)).client
p = rest.request("GET", "pages.json", params={"handle": "wholesale", "limit": 1})["pages"]
body = p[0]["body_html"]
print("body bytes:", len(body))
open("/tmp/ws_body.html", "w", encoding="utf-8").write(body)
# 表单/textarea 上下文
for m in re.finditer(r"<(form|textarea|input)[^>]*>", body):
    s = max(0, m.start() - 80)
    ctx = re.sub(r"\s+", " ", body[s:m.end() + 60])
    print("::", ctx[:200])
print("---quote hits---")
for m in re.finditer(r".{60}[Qq]uote.{60}", body):
    print("::", re.sub(r"\s+", " ", m.group(0))[:180])

# 索引真实 handle 示例
for i in range(3):
    a = rest.request("GET", "themes/190031036660/assets.json",
                     params={"asset[key]": f"assets/spec-idx-{i}.json"})["asset"]
    for it in json.loads(a.get("value") or "[]"):
        if it["m"] == "CS-AMS723MD":
            print("AMS723MD handle:", it.get("h"))
