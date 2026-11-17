"""预览通道三路探测：graphql onlineStorePreviewUrl / theme.preview_url / active 产品+预览参数。"""
import subprocess
import sys
import traceback

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

TID = 190031036660
c = ShopifyRest(StoreService().get_client(1)).client

# 路 1：graphql onlineStorePreviewUrl
try:
    d = c.graphql("query($id: ID!){ product(id: $id){ onlineStorePreviewUrl } }",
                  {"id": "gid://shopify/Product/15476051902708"})
    u = (d.get("product") or {}).get("onlineStorePreviewUrl")
    print("onlineStorePreviewUrl:", (u or "NONE")[:130])
except Exception as e:
    print("onlineStorePreviewUrl ERR:", str(e)[:120])

# 路 2：REST theme 自带 preview_url
t = c.request("GET", f"themes/{TID}.json")["theme"]
print("theme fields:", sorted(t.keys()))
pu = t.get("preview_url")
if pu:
    r = subprocess.run(["curl", "-skL", "-m", "40", "-o", "/dev/null", "-w",
                        "%{http_code} -> %{url_effective}", pu],
                       capture_output=True, text=True, timeout=50)
    print("theme preview_url curl:", r.stdout[:150])

# 路 3：active 产品公开 URL + preview_theme_id 匿名组合
ps = c.request("GET", "products.json",
               params={"limit": 1, "status": "active", "fields": "handle,online_store_url?"})
# REST 无 online_store_url 字段，直接用 handle
h = ps["products"][0]["handle"]
url = f"https://www.estrybattery.com/products/{h}?preview_theme_id={TID}"
r = subprocess.run(["curl", "-skL", "-m", "40", "-o", "/tmp/act.html", "-w",
                    "%{http_code} -> %{url_effective}", url],
                   capture_output=True, text=True, timeout=50)
print("active+preview:", r.stdout[:150])
try:
    b = open("/tmp/act.html", encoding="utf-8", errors="ignore").read()
    print("  bytes:", len(b), "| ld+json:", b.count("application/ld+json"),
          "| dawn-mark:", "estry-dawn" in b.lower() or "dawn" in b[:4000].lower())
except Exception:
    traceback.print_exc()
