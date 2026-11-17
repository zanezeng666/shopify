# -*- coding: utf-8 -*-
"""看 templates/index.json 里 image 引用格式 + Files 库文件清单。"""
import json
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

THEME_ID = 190031036660
client = StoreService().get_client(1)
rest = ShopifyRest(client).client

for key in ("templates/index.json",):
    v = rest.request("GET", f"themes/{THEME_ID}/assets.json",
                     params={"asset[key]": key})["asset"]["value"]
    refs = re.findall(r'"(shopify://[^"]+)"', v)
    print(key, "shopify refs:", sorted(set(refs))[:8])

# Files 库文件清单（确认我们转存文件的真实名字）
Q = """
query($n: Int!) {
  files(first: $n) {
    edges { node { id fileStatus ... on MediaImage { alt image { url } } } }
  }
}
"""
r = client.graphql(Q, {"n": 10})
edges = (r.get("files") or (r.get("data") or {}).get("files") or {}).get("edges", [])
for e in edges:
    n = e["node"]
    url = (n.get("image") or {}).get("url") or ""
    print("file:", n.get("id").split("/")[-1], n.get("fileStatus"), "alt=", n.get("alt"),
          "name=", url.split("/files/")[-1].split("?")[0] if "/files/" in url else "-")
