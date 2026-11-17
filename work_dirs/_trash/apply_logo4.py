# -*- coding: utf-8 -*-
"""logo 终版：复用已转存文件 -> 提取文件名 -> settings.logo=shopify://shop_images/<name>。"""
import json
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

THEME_ID = 190031036660
client = StoreService().get_client(1)
rest = ShopifyRest(client).client

FID = "gid://shopify/MediaImage/47479497851124"
Q = """
query($id: ID!) {
  node(id: $id) {
    ... on MediaImage { id fileStatus image { url } }
  }
}
"""

url = None
for _ in range(15):
    r = client.graphql(Q, {"id": FID})
    n = r.get("node") or (r.get("data") or {}).get("node") or {}
    st = n.get("fileStatus")
    if st == "READY":
        url = (n.get("image") or {}).get("url")
        break
    if st == "FAILED":
        sys.exit("file FAILED")
    time.sleep(2)

if not url:
    sys.exit("not ready / no url")
# 提取文件名: https://cdn.shopify.com/s/files/1/xxx/files/<name>?v=...
fname = url.split("/files/")[-1].split("?")[0]
print("cdn url ok, filename:", fname)

cands = [f"shopify://shop_images/{fname}", url]
v = rest.request("GET", f"themes/{THEME_ID}/assets.json",
                 params={"asset[key]": "config/settings_data.json"})["asset"]["value"]
sd = json.loads(v)

done = None
for c in cands:
    sd["current"]["logo"] = c
    sd["current"]["logo_width"] = 150
    try:
        rest.request("PUT", f"themes/{THEME_ID}/assets.json",
                     json_body={"asset": {"key": "config/settings_data.json",
                                          "value": json.dumps(sd, ensure_ascii=False, indent=2)}})
        done = c
        break
    except Exception:
        print("reject:", c[:70])
if not done:
    sys.exit("all candidates rejected")

back = json.loads(rest.request("GET", f"themes/{THEME_ID}/assets.json",
                               params={"asset[key]": "config/settings_data.json"})["asset"]["value"])["current"]
print("readback:", back.get("logo"), "| width", back.get("logo_width"))
print("PASS" if back.get("logo") == done and back.get("logo_width") == 150 else "MISMATCH")
