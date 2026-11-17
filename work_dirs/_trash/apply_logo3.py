# -*- coding: utf-8 -*-
"""logo 上文件库：fileCreate(originalSource=主题资产URL) -> READY -> settings.logo=shopify url。"""
import json
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402

THEME_ID = 190031036660
client = StoreService().get_client(1)

MUT = """
mutation FileCreate($files: [FileCreateInput!]!) {
  fileCreate(files: $files) {
    files { id fileStatus }
    userErrors { field message }
  }
}
"""
Q = """
query($id: ID!) {
  node(id: $id) {
    ... on MediaImage { id fileStatus image { url } }
  }
}
"""

pub = None  # 从主题资产自身取 public_url
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
rest = ShopifyRest(client).client
pub = rest.request("GET", f"themes/{THEME_ID}/assets.json",
                   params={"asset[key]": "assets/logo-estry.png"})["asset"].get("public_url")
print("public_url:", pub)
if not pub:
    sys.exit("no public_url")
r = client.graphql(MUT, {"files": [{"originalSource": pub, "contentType": "IMAGE"}]})
fc = r.get("fileCreate") or r.get("data", {}).get("fileCreate") or {}
print("create:", json.dumps(fc)[:300])
if fc.get("userErrors") or not fc.get("files"):
    sys.exit(1)
fid = fc["files"][0]["id"]

url = None
for _ in range(20):
    time.sleep(2)
    n = (client.graphql(Q, {"id": fid}).get("node")
         or client.graphql(Q, {"id": fid}).get("data", {}).get("node")) or {}
    st = n.get("fileStatus")
    if st == "READY":
        url = (n.get("image") or {}).get("url")
        break
    if st == "FAILED":
        print("file FAILED")
        sys.exit(1)
print("file url:", url)
if not url:
    sys.exit(1)

v = rest.request("GET", f"themes/{THEME_ID}/assets.json",
                 params={"asset[key]": "config/settings_data.json"})["asset"]["value"]
sd = json.loads(v)
sd["current"]["logo"] = url
sd["current"]["logo_width"] = 150
rest.request("PUT", f"themes/{THEME_ID}/assets.json",
             json_body={"asset": {"key": "config/settings_data.json",
                                  "value": json.dumps(sd, ensure_ascii=False, indent=2)}})
back = json.loads(rest.request("GET", f"themes/{THEME_ID}/assets.json",
                               params={"asset[key]": "config/settings_data.json"})["asset"]["value"])["current"]
print("readback:", back.get("logo", "")[:90], back.get("logo_width"))
print("PASS" if back.get("logo") == url and back.get("logo_width") == 150 else "MISMATCH")
