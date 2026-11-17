"""补跑：draft 产品预览渲染 + pages(PageFly) 兼容抽查。"""
import json
import re
import subprocess
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

BASE = "https://www.estrybattery.com"
c = ShopifyRest(StoreService().get_client(1)).client
ok = True


def curl(url):
    r = subprocess.run(["curl", "-skL", "-m", "60", "-w", "\n%{http_code}", url],
                       capture_output=True, text=True, timeout=75)
    body, _, code = r.stdout.rpartition("\n")
    return int(code or 0), body


# draft 预览（发布后 preview_key 渲染新 main = Dawn）
d = c.graphql("query($id: ID!){ product(id: $id){ onlineStorePreviewUrl } }",
              {"id": "gid://shopify/Product/15476051902708"})
u = (d.get("product") or {}).get("onlineStorePreviewUrl")
code, dp = curl(u)
types = []
for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', dp, re.S):
    try:
        types.append(json.loads(m.group(1)).get("@type"))
    except Exception:
        types.append("PARSE_FAIL")
fonts = sorted(set(re.findall(r"(oswald|assistant)_n\d", dp)))
prod_ok = "<details" in dp and "This is a" in dp
print(f"draft preview: {code} | {len(dp)}B | fonts: {fonts} | ld: {types}")
print(f"  FAQ-details: {'<details' in dp} | entity-sentence: {'This is a' in dp}"
      f" | estry-color: {'#1B2A41' in dp}")
ok &= code == 200 and "FAQPage" in types and "Product" in types and prod_ok

# pages 兼容
pages = c.request("GET", "pages.json", params={"limit": 3})["pages"]
if not pages:
    print("pages: none in store")
for pg in pages:
    code, _ = curl(f"{BASE}/pages/{pg['handle']}")
    print(f"page '{pg['handle'][:34]}': {code}")
    ok &= code == 200

print("ASSERT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
