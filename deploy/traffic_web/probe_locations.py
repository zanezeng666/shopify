"""只读探查：Shopify 仓/运费/库存水位现状，为多仓发货方案提供事实。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402

client = StoreService().get_client(1)


def g(path, params=None):
    try:
        return client.request("GET", path, params=params or {})
    except Exception as e:  # noqa: BLE001
        return {"__error__": str(e)[:180]}


out = {}

locs = g("locations.json")
if "locations" in locs:
    out["locations"] = [
        {"id": l["id"], "name": l["name"], "active": l["active"],
         "country": l.get("country_code", ""), "primary": l.get("primary", False)}
        for l in locs["locations"]
    ]
else:
    out["locations"] = locs

zones = g("shipping_zones.json")
if "shipping_zones" in zones:
    zz = []
    for z in zones["shipping_zones"]:
        cs = [c.get("country", {}).get("name") for c in z.get("countries", [])]
        rates = [
            {"name": r["name"], "price": r["price"]}
            for r in z.get("price_based_shipping_rates", [])
            + z.get("weight_based_shipping_rates", [])
        ]
        zz.append({"name": z["name"], "countries": cs[:10],
                   "n_countries": len(cs), "rates": rates})
    # 只打印摘要：zone 数 + 每组去重后的 rate 形态 + 覆盖国家数
    sig = {}
    for z in zz:
        key = json.dumps(z["rates"], ensure_ascii=False)
        sig.setdefault(key, []).append(z["name"])
    out["zones_summary"] = [
        {"rate_shape": json.loads(k)[:3], "zones": v[:6], "n_zones": len(v),
         "n_countries": sum(1 for z in zz if z["name"] in v)}
        for k, v in sig.items()
    ]
    out["zones_total"] = len(zz)
    out["zones_all_names"] = [z["name"] for z in zz]
else:
    out["zones"] = zones

pv = g("products.json", {"limit": 2, "fields": "id,title,variants"})
sample = []
for p in pv.get("products", [])[:2]:
    for v in p.get("variants", [])[:2]:
        iv = g(f"variants/{v['id']}.json",
               {"fields": "id,sku,inventory_item_id,inventory_quantity,"
                          "inventory_policy,inventory_management"})
        vd = iv.get("variant", v)
        iid = vd.get("inventory_item_id")
        lv = g("inventory_levels.json", {"inventory_item_ids": iid})
        locname = {l["id"]: l["name"] for l in out.get("locations", [])} \
            if isinstance(out.get("locations"), list) else {}
        sample.append({
            "product": p["title"][:36], "sku": vd.get("sku"),
            "tracked": vd.get("inventory_management"),
            "policy": vd.get("inventory_policy"),
            "qty_total": vd.get("inventory_quantity"),
            "levels": [{"loc": locname.get(l["location_id"], l["location_id"]),
                        "avail": l["available"]}
                       for l in lv.get("inventory_levels", [])],
        })
out["sample_variants"] = sample

print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])
