"""验证主题注入的 JSON-LD 真实渲染（draft 产品走 Shopify 预览链接）。

步骤：
1. 先试 handle?preview_theme_id（draft 通常 404）
2. GraphQL productPreviewUrl / onlineStorePreviewUrl 拿草稿预览链接
3. 预览页提取 application/ld+json → json.loads → 断言
   Product(name/sku/price)/Offer/FAQPage 全部就位
4. 复查主页 200
"""
import json
import re
import subprocess
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

THEME_ID = 136764817652
PID = 15476051902708  # ihome 样例
BASE = "https://www.bornmieo.com"

rest = ShopifyRest(StoreService().get_client(1))
c = rest.client

p = c.request("GET", f"products/{PID}.json",
              params={"fields": "handle,title"}).get("product", {})
handle, title = p["handle"], p["title"]
print("product:", title[:60], "| handle ok")


def curl(url: str) -> tuple[int, str]:
    r = subprocess.run(["curl", "-skL", "-w", "\n%{http_code}", url],
                       capture_output=True, text=True, timeout=90)
    body, _, code = r.stdout.rpartition("\n")
    return int(code or 0), body


# 1) 直接预览参数
url = f"{BASE}/products/{handle}?preview_theme_id={THEME_ID}"
code, body = curl(url)
print(f"direct preview: {code}, {len(body)}B")
if code != 200:
    # 2) GraphQL 草稿预览链接（新旧字段都试）
    for field in ("productPreviewUrl", "onlineStorePreviewUrl"):
        q = 'query($id: ID!){ product(id: $id){ %s } }' % field
        try:
            d = c.graphql(q, {"id": f"gid://shopify/Product/{PID}"})
            u = (d.get("product") or {}).get(field)
        except Exception as e:
            print(f"graphql {field}: {type(e).__name__}: {str(e)[:120]}")
            u = None
        if u:
            print(f"{field}:", u[:100])
            url, code, body = u, *curl(u)
            print(f"preview fetch: {code}, {len(body)}B")
            break
assert code == 200, f"no preview available (last {code})"

# 3) 提取并断言 JSON-LD
lds = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
                 body, re.S)
print("JSON-LD blocks on page:", len(lds))
seen_types, ok = [], True
for ld in lds:
    try:
        d = json.loads(ld)
    except json.JSONDecodeError as e:
        print("  PARSE FAIL:", e, "| head:", ld[:120])
        ok = False
        continue
    t = d.get("@type")
    seen_types.append(t)
    if t == "Product":
        v = d.get("offers", {})
        print(f"  Product: name={d.get('name','')[:50]!r}")
        print(f"    brand={d.get('brand',{}).get('name')!r} sku={d.get('sku')!r}")
        print(f"    Offer price={v.get('price')} {v.get('priceCurrency')} "
              f"avail={str(v.get('availability','')).rsplit('/',1)[-1]}")
        print(f"    image={str(d.get('image'))[:80]}")
        ok &= bool(d.get("name") and d.get("sku") and v.get("price"))
    if t == "FAQPage":
        qs = [x["name"][:40] for x in d.get("mainEntity", [])]
        print(f"  FAQPage: {len(qs)} questions: {qs}")
        ok &= len(qs) >= 3

print("types:", seen_types, "| ASSERT:", "PASS" if ok else "FAIL")

# 4) 主页复查
code, _ = curl(BASE)
print("homepage:", code)
sys.exit(0 if ok and code == 200 else 1)
