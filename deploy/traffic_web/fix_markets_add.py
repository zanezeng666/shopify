"""修复 Markets 国家覆盖缺口（31 国空 rates 根因）:
- Europe 市场补 24 国: FR NL ES SE NO PL PT HU RO SI SK LT LV EE FI CH IE DK UA RS MD MT CY LU
- International 市场补 5 国: BR CL CO NZ PE
幂等: 先读现有 regions, 只加缺失的。回滚=同结构 conditionsToDelete。
"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)

NAME2ISO = {
    "france": "FR", "netherlands": "NL", "spain": "ES", "sweden": "SE",
    "norway": "NO", "poland": "PL", "portugal": "PT", "hungary": "HU",
    "romania": "RO", "slovenia": "SI", "slovakia": "SK",
    "lithuania": "LT", "latvia": "LV", "estonia": "EE", "finland": "FI",
    "switzerland": "CH", "ireland": "IE", "denmark": "DK",
    "ukraine": "UA", "moldova": "MD", "serbia": "RS", "malta": "MT",
    "cyprus": "CY", "luxembourg": "LU", "andorra": "AD",
    "armenia": "AM", "austria": "AT", "belarus": "BY", "belgium": "BE",
    "bulgaria": "BG", "croatia": "HR", "czechia": "CZ", "germany": "DE",
    "greece": "GR", "italy": "IT", "united kingdom": "GB",
    "brazil": "BR", "chile": "CL", "colombia": "CO",
    "new zealand": "NZ", "peru": "PE",
    "congo - brazzaville": "CG", "congo - kinshasa": "CD",
    "ghana": "GH", "south africa": "ZA",
}

ADD = {
    "gid://shopify/Market/13200785652": "Europe",
    "gid://shopify/Market/466387188": "International",
}
WANT = {
    "Europe": ("FR NL ES SE NO PL PT HU RO SI SK LT LV EE FI CH IE DK "
               "UA RS MD MT CY LU").split(),
    "International": "BR CL CO NZ PE".split(),
}

LIST_Q = """
{ market(id: "%s") { id name
  conditions { regionsCondition { regions(first: 250) { nodes { name } } } } } }
"""
MUT = """
mutation M($id: ID!, $in: MarketUpdateInput!) {
  marketUpdate(id: $id, input: $in) {
    market { id name conditions { regionsCondition {
      regions(first: 250) { nodes { name } } } } }
    userErrors { field message }
  }
}
"""

for mid, mname in ADD.items():
    cur = client.graphql(LIST_Q % mid)
    m = cur["market"]
    have = set()
    for r in m["conditions"]["regionsCondition"]["regions"]["nodes"]:
        iso = NAME2ISO.get(r["name"].strip().lower())
        if iso:
            have.add(iso)
        else:
            print(f"[{mname}] 跳过未映射现有区域名: {r['name']}")
    todo = [c for c in WANT[mname] if c not in have]
    print(f"\n[{mname}] 现有 {len(have)} 国, 目标补 {len(WANT[mname])}, "
          f"实际需加 {len(todo)}: {todo}")
    if not todo:
        print(f"[{mname}] 无需变更")
        continue
    inp = {"conditions": {"conditionsToAdd": {"regionsCondition": {
        "regions": [{"countryCode": c} for c in todo]}}}}
    try:
        r = client.graphql(MUT, {"id": mid, "in": inp})
        mu = r["marketUpdate"]
        errs = mu.get("userErrors") or []
        nodes = mu["market"]["conditions"]["regionsCondition"][
            "regions"]["nodes"]
        now = {n["name"] for n in nodes}
        print(f"[{mname}] 更新后 regions={len(nodes)} userErrors={errs}")
        print(f"[{mname}] 新区域名(应含新增国): "
              f"{sorted(x for x in now if len(x) < 25)}")
    except Exception as e:
        print(f"[{mname}] EXC: {str(e)[:300]}")
    time.sleep(1)
