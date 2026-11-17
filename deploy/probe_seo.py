"""主题结构化数据能力探测：主页 JSON-LD + 主题资产里的 schema 痕迹。"""
import subprocess, re, sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

rest = ShopifyRest(StoreService().get_client(1))
c = rest.client

# 1) 主页 JSON-LD（判断主题是否输出 schema）
html = subprocess.run(["curl", "-sk", "https://www.bornmieo.com/"],
                      capture_output=True, text=True, timeout=60).stdout
print("== homepage JSON-LD ==")
for m in re.finditer(r'application/ld\+json[^>]*>(.{0,300}?)</script>',
                     html, re.S):
    print(" ", m.group(1).strip()[:200].replace("\n", " "))
print("  blocks:", len(re.findall(r"application/ld\+json", html)))
print("  password page:", "password" in html[:3000].lower())

# 2) 主题资产 grep schema
themes = c.request("GET", "themes.json").get("themes", [])
main = next((t for t in themes if t.get("role") == "main"), None)
print("\n== theme ==", main and main["name"], main and main["id"])
for key in ("sections/main-product.liquid", "layout/theme.liquid",
            "snippets/product-schema.liquid", "snippets/structured-data.liquid"):
    a = c.request("GET", f"themes/{main['id']}/assets.json",
                  params={"asset[key]": key})
    if a.get("asset"):
        body = a["asset"].get("value", "")
        hits = [w for w in ("ld+json", '"Product"', "schema.org", "FAQPage",
                            "Offer", "AggregateRating") if w in body]
        print(f"{key}: {len(body)}B, hits={hits}")
    else:
        print(f"{key}: not found")
