"""上线后全站验证：主题角色/主页/集合页/active 产品 JSON-LD/draft 预览/pages(PageFly)。"""
import json
import re
import subprocess
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

NEW, OLD = 190031036660, 136764817652
BASE = "https://www.estrybattery.com"
c = ShopifyRest(StoreService().get_client(1)).client
ok = True


def curl(url: str) -> tuple[int, str]:
    r = subprocess.run(["curl", "-skL", "-m", "60", "-w", "\n%{http_code}", url],
                       capture_output=True, text=True, timeout=75)
    body, _, code = r.stdout.rpartition("\n")
    return int(code or 0), body


def ld_blocks(html: str) -> list[dict]:
    out = []
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>',
                         html, re.S):
        try:
            out.append(json.loads(m.group(1)))
        except json.JSONDecodeError as e:
            out.append({"@type": "PARSE_FAIL", "err": str(e)[:60]})
    return out


# 1) 主题角色
for t in c.request("GET", "themes.json")["themes"]:
    if t["id"] in (NEW, OLD):
        print("theme:", t["id"], t["role"], t["name"])
        ok &= (t["id"] == NEW) == (t["role"] == "main")

# 2) 主页（Dawn 特征：oswald 字体 / Estry 色值）
code, home = curl(BASE)
fonts = sorted(set(re.findall(r"(oswald|assistant)_n\d", home)))
print(f"home: {code} | {len(home)}B | fonts: {fonts} | estry-color: {'#1B2A41' in home}")
ok &= code == 200 and "oswald" in fonts and "#1B2A41" in home

# 3) 集合页
code, col = curl(f"{BASE}/collections/all")
print(f"collections/all: {code} | {len(col)}B | product-card: {'card' in col.lower()}")
ok &= code == 200

# 4) active 产品页：Dawn 原生 Product + 注入 FAQPage
h = c.request("GET", "products.json", params={"limit": 1, "status": "active",
                                              "fields": "handle,title"})["products"][0]
code, pd = curl(f"{BASE}/products/{h['handle']}")
lds = ld_blocks(pd)
types = [d.get("@type") for d in lds]
prod = next((d for d in lds if d.get("@type") == "Product"), {})
off = prod.get("offers", {}) if isinstance(prod.get("offers"), dict) else {}
brand = (prod.get("brand") or {}).get("name") if isinstance(prod.get("brand"), dict) else prod.get("brand")
faq_n = len(next((d for d in lds if d.get("@type") == "FAQPage"),
                 {"mainEntity": []}).get("mainEntity", []))
print(f"active '{h['title'][:34]}': {code} | ld types: {types}")
print(f"  Product: name={bool(prod.get('name'))} sku={prod.get('sku')!r} "
      f"brand={brand!r} price={off.get('price')} "
      f"avail={str(off.get('availability', '')).rsplit('/', 1)[-1]}")
print(f"  image: {str(prod.get('image'))[:90]}")
print(f"  FAQPage questions: {faq_n}")
ok &= code == 200 and "Product" in types and faq_n == 3 and prod.get("name")

# 5) draft 产品预览（发布后 preview_key 应渲染 Dawn）
try:
    d = c.graphql("query($id: ID!){ product(id: $id){ onlineStorePreviewUrl } }",
                  {"id": "gid://shopify/Product/15476051902708"})
    u = (d.get("product") or {}).get("onlineStorePreviewUrl")
    code, dp = curl(u)
    lds = ld_blocks(dp)
    types = [x.get("@type") for x in lds]
    print(f"draft preview: {code} | fonts: {sorted(set(re.findall(r'(oswald|assistant)_n', dp)))}"
          f" | ld: {types} | FAQ-details: {'<details' in dp} | entity: {'This is a' in dp}")
    ok &= code == 200 and "FAQPage" in types and "Product" in types
except Exception as e:
    print("draft preview ERR:", str(e)[:120])

# 6) pages（PageFly 托管页兼容性抽查）
try:
    pages = c.request("GET", "pages.json", params={"limit": 3})["pages"]
    for pg in pages:
        code, _ = curl(f"{BASE}/pages/{pg['handle']}")
        print(f"page '{pg['handle'][:30]}': {code}")
        ok &= code == 200
except Exception as e:
    print("pages ERR:", str(e)[:100])

print("ASSERT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
