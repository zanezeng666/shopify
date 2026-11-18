"""Factory Direct 区块进默认模板 templates/product.json（全店产品页生效），样板产品切回默认模板。幂等。"""
import json
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

TID = 190031036660
PRODUCT_ID = 4638608261220
KEY = "templates/product.json"
c = ShopifyRest(StoreService().get_client(1)).client


def get_asset(key):
    try:
        return c.request("GET", f"themes/{TID}/assets.json", params={"asset[key]": key})["asset"].get("value", "") or ""
    except Exception:
        return ""


raw = get_asset(KEY)
assert raw, "templates/product.json 不存在"
t = json.loads(raw)
stamp = time.strftime("%Y%m%d_%H%M")

main_sec = None
for k in t.get("order", []):
    if t["sections"][k].get("type") == "main-product":
        main_sec = k
        break
assert main_sec, "未找到 main-product section"

blocks = t["sections"][main_sec].get("blocks", {})
block_order = t["sections"][main_sec].get("block_order", [])
print("main section:", main_sec, "| blocks:", len(blocks), "| order:", block_order)

if any(b.get("type") == "factory_direct" for b in blocks.values()):
    print("默认模板已含 factory_direct，跳过")
else:
    with open(f"/home/jason/shopify-admin/deploy/backups/{stamp}__templates__product.json", "w") as f:
        f.write(raw)
    price_ids = [bid for bid in block_order if blocks.get(bid, {}).get("type") == "price"]
    assert len(price_ids) == 1, f"price block 数异常: {price_ids}"
    new_bid = "fd_note" if "fd_note" not in blocks else "fd_note_2"
    blocks[new_bid] = {"type": "factory_direct", "settings": {}}
    block_order.insert(block_order.index(price_ids[0]) + 1, new_bid)
    t["sections"][main_sec]["blocks"] = blocks
    t["sections"][main_sec]["block_order"] = block_order
    c.request("PUT", f"themes/{TID}/assets.json",
              json_body={"asset": {"key": KEY, "value": json.dumps(t, ensure_ascii=False, indent=2)}})
    ok = False
    for _ in range(5):
        time.sleep(2)
        if "factory_direct" in get_asset(KEY):
            ok = True
            break
    print("默认模板更新:", "OK" if ok else "回读超时", "| order:", block_order)

# 样板产品切回默认模板（统一来源，专属模板资产保留不引用）
cur = c.request("GET", f"products/{PRODUCT_ID}.json", params={"fields": "template_suffix"})["product"].get("template_suffix")
if not cur:
    print("样板产品已是默认模板")
else:
    c.request("PUT", f"products/{PRODUCT_ID}.json", json_body={"product": {"id": PRODUCT_ID, "template_suffix": ""}})
    p = c.request("GET", f"products/{PRODUCT_ID}.json", params={"fields": "template_suffix"})["product"]
    print(f"样板产品切回默认: template_suffix={p['template_suffix']!r}")
