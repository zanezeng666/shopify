# -*- coding: utf-8 -*-
"""Basic 套餐原生运费规则配置（B 方案，GraphQL deliveryProfileUpdate）。

REST shipping_zones 是只读资源（PUT 406），写入走 General profile：
  deliveryProfileUpdate -> locationGroupsToUpdate -> zonesToUpdate(增量)
    -> methodDefinitionsToCreate(固定价 + 重量/价格条件)

方案（重量档边界错开 1g 避免重叠）：
  US    <=999g $5.99 / 1.0-1.999kg $9.99 / >=2kg $14.99，满 $69 免运费
  CA    $9.99/$14.99/$19.99，满 $99 免运费
  MX    $12.99/$17.99/$22.99
  UK/EU $14.99/$19.99/$24.99
  偏远  $19.99/$24.99/$29.99
幂等：先查 zone 现有 methodDefinitions，同次 mutation 内先删后建。
用法：python setup_shipping_rates.py [--only US] [--dry-run]
"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService

SPEED = {"US": "3-6 business days", "CA": "5-10 business days",
         "MX": "5-12 business days"}
SPEED_DEFAULT = "8-15 business days"

# cc -> ([(price, lo_kg|None, hi_kg|None, name_override|None)], free_min|None)
# US: <=1kg $5.99 / 1-3kg $9.99 / 3kg+ 免；满 $69 免（对齐已确认方案）
# MX: 维持现状无条件免邮
GROUPS = {
    "US": ([("5.99", None, 0.999, None), ("9.99", 1.0, 2.999, None),
            ("0.00", 3.0, None, "Free Shipping (orders over 3kg)")], 69),
    "CA": ([("9.99", None, 0.999, None), ("14.99", 1.0, 1.999, None),
           ("19.99", 2.0, None, None)], 99),
    "MX": ([("0.00", None, None, "Free Shipping (5-12 business days)")], None),
}
EU = ["GB", "HU", "LV", "LT", "LU", "MT", "MC", "NL", "PL", "PT", "RO",
      "SK", "SI", "ES", "SE", "UA"]
REMOTE = ["NO", "CH", "ZA", "GP", "NC", "PG", "LC", "VU"]
for cc in EU:
    GROUPS[cc] = ([("14.99", None, 0.999, None), ("19.99", 1.0, 1.999, None),
                   ("24.99", 2.0, None, None)], None)
for cc in REMOTE:
    GROUPS[cc] = ([("19.99", None, 0.999, None), ("24.99", 1.0, 1.999, None),
                   ("29.99", 2.0, None, None)], None)

USD = "USD"

def money(a: str) -> dict:
    return {"amount": a, "currencyCode": USD}

def methods_for(cc: str) -> list[dict]:
    tiers, free_min = GROUPS[cc]
    speed = SPEED.get(cc, SPEED_DEFAULT)
    name = f"Standard Shipping ({speed})"
    out = []
    for price, lo, hi, name_ov in tiers:
        m = {"name": name_ov or name, "active": True,
             "rateDefinition": {"price": money(price)}}
        conds = []
        if lo is not None:
            conds.append({"criteria": {"value": lo, "unit": "KILOGRAMS"},
                          "operator": "GREATER_THAN_OR_EQUAL_TO"})
        if hi is not None:
            conds.append({"criteria": {"value": hi, "unit": "KILOGRAMS"},
                          "operator": "LESS_THAN_OR_EQUAL_TO"})
        if conds:
            m["weightConditionsToCreate"] = conds
        out.append(m)
    if free_min is not None:
        out.append({
            "name": f"Free Shipping (orders ${free_min}+)", "active": True,
            "rateDefinition": {"price": money("0.00")},
            "priceConditionsToCreate": [{
                "criteria": money(str(free_min)),
                "operator": "GREATER_THAN_OR_EQUAL_TO"}],
        })
    return out

Q_READ = """
query P($id: ID!) { deliveryProfile(id: $id) {
  id name version
  profileLocationGroups {
    locationGroup { id }
    locationGroupZones(first: 100) { edges { node {
      zone { id name }
      methodDefinitions(first: 100) { edges { node {
        id name active
        rateProvider { __typename }
      } } }
    } } }
  }
} }
"""

M_UPDATE = """
mutation U($id: ID!, $profile: DeliveryProfileInput!) {
  deliveryProfileUpdate(id: $id, profile: $profile) {
    profile { id version zoneCountryCount }
    userErrors { field message }
  }
} """

def main() -> None:
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    dry = "--dry-run" in sys.argv
    c = StoreService().get_client(1)

    zones = c.request("GET", "shipping_zones.json").get("shipping_zones", [])
    # REST zone -> (zone_gid, profile_gid, group_gid)
    zmap = {}
    for z in zones:
        cc = (z.get("countries") or [{}])[0].get("code")
        zmap[cc] = (z.get("admin_graphql_api_id"), z.get("profile_id"),
                    z.get("location_group_id"), z["name"])
    ccs = [cc for cc in GROUPS if cc in zmap and (not only or cc == only)]
    print(f"[1] 目标 {len(ccs)} 个国家区" + (f"（only={only}）" if only else ""))

    profile_gid = next(v[1] for v in zmap.values() if v[1])
    prof = (c.graphql(Q_READ, {"id": profile_gid}) or {}).get("deliveryProfile")
    if not prof:
        print("!! 读 profile 失败")
        return
    existing: dict[str, list[dict]] = {}  # zone_gid -> method nodes
    lgid_by_zone = {}
    for lg in prof.get("profileLocationGroups", []):
        for e in lg.get("locationGroupZones", {}).get("edges", []):
            node = e["node"]
            zgid = node.get("zone", {}).get("id")
            if not zgid:
                continue
            existing[zgid] = [ve["node"] for ve in
                             node.get("methodDefinitions", {}).get("edges", [])]
            lgid_by_zone[zgid] = lg.get("locationGroup", {}).get("id")
    print(f"[2] profile version={prof.get('version')} zones_with_methods="
          f"{sum(1 for v in existing.values() if v)}")

    ok = fail = 0
    for cc in ccs:
        zone_gid, _, _, zname = zmap[cc]
        tgt = methods_for(cc)
        if dry:
            print(f"  DRY {cc:3} {zname!r} methods={len(tgt)} "
                  f"existing={len(existing.get(zone_gid, []))}")
            continue
        profile_in: dict = {"locationGroupsToUpdate": [{
            "id": lgid_by_zone.get(zone_gid) or zmap[cc][2],
            "zonesToUpdate": [{"id": zone_gid,
                               "methodDefinitionsToCreate": tgt}],
        }]}
        # 只删固定价/占位 rate（DeliveryRateDefinition），保留 CCS participant
        stale = [m["id"] for m in existing.get(zone_gid, [])
                 if (m.get("rateProvider") or {}).get("__typename")
                 == "DeliveryRateDefinition"]
        if stale:
            profile_in["methodDefinitionsToDelete"] = stale
        r = (c.graphql(M_UPDATE, {"id": profile_gid, "profile": profile_in})
             or {}).get("deliveryProfileUpdate", {})
        errs = r.get("userErrors") or []
        if errs:
            fail += 1
            print(f"  ERR {cc} {zname!r}: {errs[:2]}")
        else:
            ok += 1
            print(f"  OK  {cc:3} {zname!r:20} methods={len(tgt)}"
                  + (" +删旧" if stale else ""))
    print(f"[3] 完成 ok={ok} fail={fail}" + ("（DRY）" if dry else ""))

if __name__ == "__main__":
    main()
