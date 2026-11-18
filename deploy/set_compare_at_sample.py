"""样板 SKU 划线价写入（幂等/可回滚）。
用法:
  set            -> compare_at_price = 22.99（18.99×1.18≈22.41 → .99 心理价，展示 -17%）
  clear          -> 置空恢复
  (无参)          -> 只读现状
"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

VARIANT_ID = 32058744176740
COMPARE_AT = "22.99"

c = ShopifyRest(StoreService().get_client(1)).client
v = c.request("GET", f"variants/{VARIANT_ID}.json", params={"fields": "id,title,price,compare_at_price,sku"})["variant"]
print(f"现状: variant={VARIANT_ID} title={v['title']!r} price={v['price']} "
      f"compare_at={v.get('compare_at_price')} sku={v.get('sku')}")

act = sys.argv[1] if len(sys.argv) > 1 else ""
if act == "set":
    if v.get("compare_at_price") == COMPARE_AT:
        print("已为目标值，跳过")
    else:
        c.request("PUT", f"variants/{VARIANT_ID}.json",
                  json_body={"variant": {"id": VARIANT_ID, "compare_at_price": COMPARE_AT}})
        v2 = c.request("GET", f"variants/{VARIANT_ID}.json",
                       params={"fields": "price,compare_at_price"})["variant"]
        pct = round((1 - float(v2["price"]) / float(v2["compare_at_price"])) * 100) if v2.get("compare_at_price") else 0
        print(f"写入后: price={v2['price']} compare_at={v2['compare_at_price']} -> 折扣约 -{pct}%")
elif act == "clear":
    c.request("PUT", f"variants/{VARIANT_ID}.json",
              json_body={"variant": {"id": VARIANT_ID, "compare_at_price": None}})
    v2 = c.request("GET", f"variants/{VARIANT_ID}.json", params={"fields": "compare_at_price"})["variant"]
    print(f"已清除: compare_at={v2.get('compare_at_price')}")
