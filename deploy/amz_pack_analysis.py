# -*- coding: utf-8 -*-
"""20 样本：体系内亚马逊全店价格 -> Pack 折算单价 -> 主流价 -> vs Shopify 价。
数据源（服务器拉回）：
  amz_probe2.json  amazon_inventory 多期库存快照（每店每listing取最新价）
  amz_probe3.json  all_listings_report 2026-11-06 快照（标题判 Pack + 现价）
"""
import json
import re
import statistics as st

DEP = r"e:\worksapce\shopify\deploy"
OUR = {  # v2 存档的 Shopify 现价
    "CS-HIQ200SL": 30.99, "CS-TOX500TW": 35.99, "CS-DEL552NB": 44.99,
    "CS-SMR365SH": 19.99, "CS-ABL100VX": 139.99, "CS-MVS500VX": 27.99,
    "CS-CHM170PR": 20.99, "CS-FNT250TW": 31.99, "CS-TMG610SL": 19.99,
    "CS-ABM600SL": 30.99, "CS-SFM3SL": 19.99, "CS-DEW528PX": 62.99,
    "CS-EMC150LS": 27.99, "CS-KOH300MD": 27.99, "CS-FVA034MD": 28.99,
    "CS-ECR131VX": 27.99, "CS-P303CL": 18.99, "CS-RMA150MD": 82.99,
    "CS-WGF300VX": 21.99, "CS-BS3300PX": 62.99,
}
ITEM = {
    "CS-HIQ200SL": "HP iPAQ 210", "CS-TOX500TW": "Tait Orca 5000",
    "CS-DEL552NB": "Dell Precision 3560", "CS-SMR365SH": "三星 Gear Fit2 Pro",
    "CS-ABL100VX": "Wolf Garten 割草机", "CS-MVS500VX": "小米 G1 扫地机",
    "CS-CHM170PR": "NTN LT2001 寻呼机", "CS-FNT250TW": "八重洲 FT-25R",
    "CS-TMG610SL": "TomTom Go610", "CS-ABM600SL": "Lenovo ServeRaid",
    "CS-SFM3SL": "i-Audio X5", "CS-DEW528PX": "DeWalt DC528",
    "CS-EMC150LS": "Saft 0120894 应急灯", "CS-KOH300MD": "IKO3 心电图",
    "CS-FVA034MD": "Fresenius 输液泵", "CS-ECR131VX": "Ilife A4S",
    "CS-P303CL": "Radio Shack 431021", "CS-RMA150MD": "ResMed Astral150",
    "CS-WGF300VX": "Mannesmann 工具", "CS-BS3300PX": "Ramset SBD12",
}
US = "ATVPDKIKX0DER"

PACK_PATS = [
    (re.compile(r"(\d+)\s*[- ]?\s*packs?\b", re.I), "pack"),
    (re.compile(r"\bpack\s+of\s+(\d+)", re.I), "pack"),
    (re.compile(r"(\d+)\s*[- ]?\s*pcs\b", re.I), "pcs"),
    (re.compile(r"(\d+)\s*[- ]?\s*pieces?\b", re.I), "pcs"),
    (re.compile(r"(\d+)\s*[- ]?\s*pc\b", re.I), "pcs"),
]
XDIG = re.compile(r"\bx\s*[- ]?\s*(\d+)\b", re.I)
MODEL_X = re.compile(r"\bx[- ]?5\b", re.I)  # iAudio X5 型号词保护


def pack_of(name: str, cs_id: str) -> int:
    best = 0
    for pat, _g in PACK_PATS:
        for m in pat.finditer(name):
            v = int(m.group(1))
            if 1 <= v <= 20:
                best = max(best, v)
    if best:
        return best
    if cs_id == "CS-SFM3SL":      # 标题必含 X5 型号，x\d 规则禁用
        return 1
    m = XDIG.search(name)
    if m and 1 <= int(m.group(1)) <= 10 and not MODEL_X.search(name):
        return int(m.group(1))
    return 1


def tofloat(s):
    if s is None:
        return None
    m = re.search(r"\d+(?:\.\d+)?", str(s).replace(",", ""))
    return float(m.group(0)) if m else None


inv = json.load(open(f"{DEP}\\amz_probe2.json", encoding="utf-8"))["inventory_rows"]
alr = json.load(open(f"{DEP}\\amz_probe3.json", encoding="utf-8"))["alr_rows"]

# 1) inventory：美国站，每 (cs_id, store, asin, sku) 取最新 add_date 价
inv_latest = {}
for r in inv:
    if r["market_id"] != US or not r["price"]:
        continue
    p = tofloat(r["price"])
    if not p or p <= 0:
        continue
    key = (r["cs_id"], r["store_name"], r["asin"], r["sku"])
    d = r["add_date"] or ""
    if key not in inv_latest or d > inv_latest[key][0]:
        inv_latest[key] = (d, p)

# 2) alr：美国站在售 listing（有标题+可选现价）
rows = [r for r in alr if r["mkt"] == US]

# 3) 合并：alr 行优先其 price，缺失用 inv_latest 同键补
units = {}   # cs_id -> list[dict]
for r in rows:
    cs = r["cs_id"]
    p = tofloat(r["price"])
    if not p or p <= 0:
        got = inv_latest.get((cs, r["store"], r["asin"], r["sku"]))
        if got:
            p = got[1]
    if not p or p <= 0:
        continue
    qty = pack_of(r["name"], cs)
    units.setdefault(cs, []).append({
        "store": r["store"], "asin": r["asin"], "p": p, "qty": qty,
        "u": round(p / qty, 2), "name": r["name"][:90], "src": "alr",
    })
# alr 没覆盖的样本：直接用 inventory 最新价（无标题，pack=1，标注）
covered = set(units)
for (cs, store, asin, sku), (d, p) in inv_latest.items():
    if cs in covered and cs in units:
        continue
    if cs not in OUR:
        continue
    units.setdefault(cs, []).append({
        "store": store, "asin": asin, "p": p, "qty": 1, "u": round(p, 2),
        "name": f"(inv {d})", "src": "inv",
    })

# 4) 汇总（写 UTF-8 文件，控制台 GBK 会乱码）
lines = []
P = lines.append
P("=" * 110)
for cs in OUR:
    lst = units.get(cs, [])
    if not lst:
        P(f"\n### {cs} {ITEM[cs]}  我方Shopify=${OUR[cs]}  体系内无美国站报价")
        continue
    us_ = sorted(x["u"] for x in lst)
    n = len(us_)
    q1, med, q3 = (st.quantiles(us_, n=4)[:3] if n >= 4
                   else (min(us_), st.median(us_), max(us_)))
    lo, hi = q1 - 1.5 * (q3 - q1 or med * 0.4), q3 + 1.5 * (q3 - q1 or med * 0.4)
    core = [v for v in us_ if lo <= v <= hi] or us_
    main = round(st.median(core), 2)
    adv = round((main - OUR[cs]) / main * 100, 1) if main else 0
    P(f"\n### {cs} {ITEM[cs]}  我方Shopify=${OUR[cs]} | 体系n={n} "
      f"主流=${main} 核心区[${round(min(core),2)}~${round(max(core),2)}] "
      f"我方vs主流{adv:+.0f}%")
    # 明细：每店一行（含多Pack），主流簇内标注*
    for x in sorted(lst, key=lambda z: z["u"]):
        mark = "*" if lo <= x["u"] <= hi else " "
        P(f"  {mark} {x['store'][:12]:12} ${x['p']:>8.2f}/x{x['qty']} "
          f"= ${x['u']:>7.2f}  {x['name'][:62]}")
    if n >= 4:
        outs = [x for x in lst if not (lo <= x["u"] <= hi)]
        if outs:
            P(f"  -- 剔除离群 {len(outs)} 条: " +
              ", ".join(f"{x['store']}${x['u']}" for x in outs[:6]) +
              ("..." if len(outs) > 6 else ""))

with open(f"{DEP}\\amz_pack_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("written", len(lines), "lines")
