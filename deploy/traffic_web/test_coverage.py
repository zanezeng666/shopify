"""发货国家覆盖 + 价格合理性全量核对。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)

# 1) checkout 放行国家（Shopify 按 zone 派生的可结账国家）
ships = set()
try:
    r = client.graphql("{ shop { shipsToCountries } }")
    ships = set(r["shop"]["shipsToCountries"])
except Exception as e:
    print("shipsToCountries 查询失败:", str(e)[:150])

# 2) REST zone 实况
zones = client.request("GET", "shipping_zones.json").get("shipping_zones", [])
zc = {}
for z in zones:
    rates = z.get("price_based_shipping_rates", []) + \
        z.get("weight_based_shipping_rates", [])
    for c in z.get("countries", []):
        zc[c["code"]] = sorted(
            [(rr.get("weight_low") or 0, rr.get("weight_high") or 9999,
              rr["name"], float(rr["price"])) for rr in rates])

plan = json.load(open("/home/jason/traffic-web/cfg_shipping/plan.json"))
pc = {}
for z in plan["zones"]:
    for c in z["countries"]:
        pc[c] = [(float(r["price"]), r["low_kg"], r["high_kg"], r["name"])
                 for r in z["rates"]]

print(f"\n== 覆盖 == zone 实配 {len(zc)} 国 | plan {len(pc)} 国 | "
      f"checkout 放行 {len(ships)} 国")
if ships:
    print("plan 有但 checkout 不放行:", sorted(set(pc) - ships) or "无")
    print("checkout 放行但 plan 外:", sorted(ships - set(pc)) or "无")

print("\n== zone 实配国家清单 ==")
print(" ".join(sorted(zc)))

# 3) 价格核对（REST 实际 vs plan）
bad = 0
for c in sorted(pc):
    rest = zc.get(c)
    if rest is None:
        print(f"  {c}: 缺 zone!")
        bad += 1
        continue
    rest_p = sorted(p for (_, _, _, p) in rest)
    plan_p = sorted(p for (p, _, _, _) in pc[c])
    if rest_p != plan_p:
        bad += 1
        print(f"  {c}: 不一致 rest={rest_p} plan={plan_p}")
print(f"价格不一致国家数: {bad}")

# 4) 买家视角账本
print("\n== 买家运费（T1 单件≤450g 档）==")
free_list, paid = [], []
for c in sorted(pc):
    t1 = min(p for (p, _, _, _) in pc[c])
    if t1 == 0:
        free_list.append(c)
    else:
        paid.append((c, t1))
print(f"免邮国 {len(free_list)} 个: {' '.join(free_list)}")
paid.sort(key=lambda x: x[1])
line = "  ".join(f"{c}=${p:.2f}" for c, p in paid)
print(f"付费国 {len(paid)} 个: {line}")

# 5) 成本复核（plan detail vs REST 展示差价）
detail = plan.get("detail", {})
print("\n== 抽样成本账（售价 $18.99 已含美国运费 F_us）==")
print("国家 | T1运费 | 渠道成本T1 | F_us(T1) | 理论差价 | 核对")
for c in ("US", "GB", "DE", "AU", "BR", "RU", "MX", "JP", "VN"):
    if c not in detail:
        print(f"  {c}: detail 缺")
        continue
    d = detail[c]
    t1 = min(p for (p, _, _, _) in pc[c]) if c in pc else None
    print(f"  {c}: detail={json.dumps(d, ensure_ascii=False)[:160]} T1=${t1}")
