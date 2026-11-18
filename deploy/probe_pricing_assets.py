"""只读：确认主题价格渲染（compare_at/划线价/badge）+ 样板产品变体现状。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

TID = 190031036660
HANDLE = "battery-for-creative-zen-vision-m-zen-vision-m-video-ba20603r79914-dvp-hd0003"
c = ShopifyRest(StoreService().get_client(1)).client

# 0) live 主题确认
themes = c.request("GET", "themes.json")["themes"]
live = [t for t in themes if t["role"] == "main"]
print("live theme:", live[0]["id"], live[0]["name"] if live else "!")


def get(key: str) -> str:
    return c.request("GET", f"themes/{TID}/assets.json",
                     params={"asset[key]": key})["asset"].get("value", "") or ""


# 1) price.liquid —— compare_at 渲染是否保留
price = get("snippets/price.liquid")
print(f"\n[price.liquid] bytes={len(price)}")
for pat in ("compare_at_price", "compare_at", "on-sale", "regular", "sale_price"):
    print(f"  '{pat}' hits={price.count(pat)}")
# 打印价格单元核心结构（前后各截一段）
i = price.find("compare_at_price")
if i > 0:
    print("  --- excerpt ---")
    print("  " + price[max(0, i - 300):i + 500].replace("\n", "\n  "))

# 2) main-product.liquid —— 价格区位置（Factory Direct 区块锚点）
mp = get("sections/main-product.liquid")
print(f"\n[main-product.liquid] bytes={len(mp)}")
for pat in ("render 'price'", "badge", "on-sale", "sale_badge", "price--sale"):
    print(f"  '{pat}' hits={mp.count(pat)}")
i = mp.find("render 'price'")
if i > 0:
    print("  --- price block context ---")
    print("  " + mp[max(0, i - 600):i + 700].replace("\n", "\n  "))

# 3) 卡片 sale badge
card = get("snippets/card-product.liquid")
print(f"\n[card-product.liquid] bytes={len(card)}")
for pat in ("compare_at_price", "badge--bottom-left", "on-sale", "translations.featured"):
    print(f"  '{pat}' hits={card.count(pat)}")

# 4) 样板产品变体现状
ps = c.request("GET", "products.json", params={"handle": HANDLE, "fields": "id,title,variants,handle"})
plist = ps.get("products", [])
if not plist:
    print("\n[product] NOT FOUND by handle!")
else:
    p = plist[0]
    print(f"\n[product] id={p['id']} title={p['title'][:60]}")
    for v in p["variants"]:
        print(f"  variant id={v['id']} title={v['title']!r} price={v['price']} "
              f"compare_at={v.get('compare_at_price')} sku={v.get('sku')}")
