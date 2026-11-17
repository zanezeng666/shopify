# -*- coding: utf-8 -*-
"""只读挖词 v2：ad_medical 选品池(cs_id) -> device 表适配机型 -> Search 词表。

v2 清洗升级：
- 剔除非医疗品牌（Anritsu 射频仪器/Compex 运动 EMS）
- 品牌名规范化（去公司后缀、连字符转空格、剥与品牌重复的 token）
- 型号去描述性词（MONITOR/VITAL/SIGNS/STATION...），拒绝纯数字<4位
- 裸型号词仅保留含字母的型号（纯数字歧义大）
"""
import json
import re
import unicodedata
from collections import defaultdict

from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine

DEP = "/home/jason/shopify-admin/deploy"
POOL = f"{DEP}/ad_medical_selected.json"
OUT = f"{DEP}/med_search_keywords.json"
URL = "https://www.estrybattery.com/collections/medical-battery"

CORE_RX = re.compile(
    r"^(CR|ICR|INR|NCR|UR|LR|LF|IMR|LI[- ]?ION|LI[- ]?PO)[- ]?\d{3,5}", re.I)
EXCLUDE_BRANDS = {"ANRITSU", "COMPEX"}
POLICY_TOKENS = {"DENSHI"}  # 電子=日语电子烟关联词，Google 烟草政策拦截
BRAND_STRIP = {"HEALTHCARE", "MEDICALSYSTEMS", "SYSTEMS", "MEDICAL", "INC",
               "CORP", "LIMITED", "LTD", "TECHNOLOGIES", "TECHNOLOGY",
               "GROUP", "COMPANY", "INTERNATIONAL"} | POLICY_TOKENS
MODEL_JUNK = {"MONITOR", "PATIENT", "VENTILATOR", "ANESTHESIA", "ANALYZER",
              "ANALYZERS", "STATION", "CABLE", "ANTENNA", "SELECT", "VITAL",
              "SIGNS", "MACHINE", "FETAL", "MEMORY", "ENERGY", "ENEGRY",
              "READY", "SYSTEM", "BASE", "EXPRESS", "AND", "THE", "WITH",
              "FOR", "IN", "NEW", "TYPE", "BATTERY", "INFUSION", "INFUSIONS",
              "PUMP", "PUMPS", "OXIMETER", "PULSE", "ECG", "MED"}
GENERIC_MODELS = {"BATTERY", "BATTERIES", "MEDICAL", "DEVICE", "UNIT",
                  "MODULE", "PACK", "CELL", "SERIES", "MODEL", "EQUIPMENT"}
MAX_BRAND_GROUPS = 8
MAX_MODELS_PER_GROUP = 15


def clean_brand(raw: str) -> str:
    b = unicodedata.normalize("NFKC", str(raw))
    b = b.replace("-", " ")
    toks = [t for t in re.split(r"\s+", b.strip()) if t]
    toks = [t for t in toks if t.upper() not in BRAND_STRIP]
    return " ".join(toks).strip()


def clean_model(raw: str, brand_words: set) -> str | None:
    m = unicodedata.normalize("NFKC", str(raw)).upper()
    m = re.sub(r"\s+", " ", m).strip(" -.,;:/")
    toks = [t for t in m.split(" ") if t]
    toks = [t for t in toks if t not in MODEL_JUNK]
    toks = [t for t in toks if t not in brand_words]  # 剥与品牌重复 token
    toks = [t for t in toks if t not in POLICY_TOKENS]
    while toks and len(toks[-1]) == 1 and not toks[-1].isdigit():
        toks.pop()  # 尾部孤立字母（"DATEX-OHMEDA S"）
    m = " ".join(toks)
    if not m or len(m) < 3 or len(m) > 30 or m in GENERIC_MODELS:
        return None
    if CORE_RX.match(m):
        return None
    return m


def main() -> None:
    pool = json.load(open(POOL, encoding="utf-8"))["selected"]
    csids = sorted({p["cs_id"] for p in pool if p.get("cs_id")})
    print(f"选品池: {len(pool)} 个产品 / {len(csids)} 个 cs_id")

    eng = get_cs_engine()
    rows = []
    with eng.connect() as c:
        rows += c.execute(text(
            "SELECT cs_id, brand, device_model FROM device "
            "WHERE LOWER(category) LIKE '%medical%'"
        )).all()
        for i in range(0, len(csids), 200):
            chunk = csids[i:i + 200]
            ph = ",".join(f":c{j}" for j in range(len(chunk)))
            rows += c.execute(text(
                f"SELECT cs_id, brand, device_model FROM device "
                f"WHERE cs_id IN ({ph})"),
                {f"c{j}": v for j, v in enumerate(chunk)}).all()
    seen = set()
    uniq = []
    for r in rows:
        k = (r[0], r[1], r[2])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    print(f"device 相关行: 去重 {len(uniq)}")

    bm = defaultdict(lambda: defaultdict(int))
    skipped = defaultdict(int)
    for csid, brand, model in uniq:
        if not brand or not model:
            continue
        b = clean_brand(brand)
        if not b or b.upper() in EXCLUDE_BRANDS:
            skipped[brand] += 1
            continue
        for part in re.split(r"[/,;]", str(model)):
            m = clean_model(part, {w.upper() for w in b.split()})
            if m:
                bm[b][m] += 1
            else:
                skipped["(bad model)"] += 1
    print(f"清洗后 brand 数={len(bm)}  剔除明细={dict(skipped)}")

    brands = sorted(bm.items(), key=lambda kv: len(kv[1]), reverse=True)
    print("\n品牌分布(清洗后型号数):")
    for b, ms in brands[:14]:
        print(f"  {b}: {len(ms)} 型号, top={sorted(ms.items(), key=lambda x: -x[1])[:3]}")

    ad_groups = []
    for b, ms in brands[:MAX_BRAND_GROUPS]:
        if len(ms) < 5:
            continue
        kws = [
            {"text": f"{b} battery", "match": "PHRASE"},
            {"text": f"{b} battery", "match": "EXACT"},
            {"text": f"{b} medical device battery", "match": "PHRASE"},
        ]
        top = sorted(ms.items(), key=lambda x: -x[1])[:MAX_MODELS_PER_GROUP]
        for m, _n in top:
            bm_kw = f"{b} {m} battery"
            if len(bm_kw) <= 60:
                kws.append({"text": bm_kw, "match": "PHRASE"})
                kws.append({"text": bm_kw, "match": "EXACT"})
            if re.search(r"[A-Z]", m) and len(m) >= 4:
                kws.append({"text": f"{m} battery", "match": "PHRASE"})
        dedup = {(k["text"], k["match"]) for k in kws}
        kws = [{"text": t, "match": mt} for (t, mt) in dedup]
        ad_groups.append({"name": b, "keywords": kws})

    generic = []
    for t in ["patient monitor battery", "defibrillator battery",
              "medical device battery replacement", "ecg machine battery",
              "ventilator battery", "infusion pump battery",
              "pulse oximeter battery", "medical battery replacement",
              "patient monitor battery replacement",
              "defibrillator battery replacement"]:
        generic.append({"text": t, "match": "PHRASE"})
    ad_groups.append({"name": "Medical Generic", "keywords": generic})

    NEG_EXACT = ["free", "manual", "pdf", "datasheet", "wiki", "job", "jobs",
                 "salary", "course", "training", "certification", "recycle",
                 "recycling", "disposal", "watch", "hearing", "laptop",
                 "phone", "iphone", "aa", "aaa", "9v", "car", "golf", "boat"]
    NEG_PHRASE = ["service manual", "repair guide", "how to test",
                  "battery charger", "cross reference chart"]

    plan = {
        "campaign_name": "Estry Medical Search",
        "url": URL,
        "negatives": ([{"text": t, "match": "EXACT"} for t in NEG_EXACT]
                      + [{"text": t, "match": "PHRASE"} for t in NEG_PHRASE]),
        "ad_groups": ad_groups,
    }
    json.dump(plan, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(f"\n=== 词表落盘 {OUT} ===")
    total = 0
    for g in ad_groups:
        n = len(g["keywords"])
        total += n
        print(f"[{g['name']}] {n} 词")
        for k in g["keywords"][:8]:
            print(f"    {k['match']:6} {k['text']}")
    print(f"ad_groups={len(ad_groups)} 关键词总数={total} "
          f"负词={len(plan['negatives'])}")


if __name__ == "__main__":
    main()
