# -*- coding: utf-8 -*-
"""各分类搜索广告计划生成（dry，只读）。

数据源：远端active产品(权威) + /tmp/cat_brands.json(recon2产物) + cs_new.device挖词
产出：/tmp/allcat_plans.json — 每分类 {campaign, url, path1, ad_groups, headlines, descriptions}
纳入判据：远端active产品数>=10 且非Medical(已有campaign)
"""
import json
import re
import time
from collections import Counter

from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine
from shopify_admin.services.stores.service import StoreService

# product_type → (short 广告用名, stem 词根, collection handle, CS分类)
MAP = {
    "Cordless Phone Battery": ("Cordless Phone Battery", "cordless phone",
                               "cordless-phone-battery", "Cordless Phone"),
    "Equipment, Survey, Test Battery": ("Test Equipment Battery",
                                        "survey equipment",
                                        "equipment-survey-test-battery",
                                        "Equipment, Survey, Test"),
    "Vacuum Battery": ("Vacuum Battery", "vacuum", "vacuum-battery", "Vacuum"),
    "Two-Way Radio Battery": ("Two-Way Radio Battery", "two-way radio",
                              "two-way-radio-battery", "Two-Way Radio"),
    "GPS, Navigator Battery": ("GPS Navigator Battery", "gps navigator",
                               "gps-navigator-battery", "GPS, Navigator"),
    "Barcode Scanner Battery": ("Barcode Scanner Battery", "barcode scanner",
                                "barcode-scanner-battery-1",
                                "Barcode Scanner"),
    "Power Tools Battery": ("Power Tool Battery", "power tool",
                            "power-tools-battery", "Power Tools"),
    "Speaker Battery": ("Speaker Battery", "speaker", "speaker-battery",
                        "Speaker"),
    "Wireless Headset Battery": ("Wireless Headset Battery", "wireless headset",
                                 "wireless-headset-battery",
                                 "Wireless Headset"),
    "Dog Collar Battery": ("Dog Collar Battery", "dog collar",
                           "dog-collar-battery", "Dog Collar"),
    "Tablet Battery": ("Tablet Battery", "tablet", "tablet-battery", "Tablet"),
    "Crane Remote Control Battery": ("Crane Remote Battery", "crane remote",
                                     "crane-remote-control-battery",
                                     "Crane Remote Control"),
    "Media Player Battery": ("Media Player Battery", "media player",
                             "media-player-battery", "Media Player"),
    "Shaver Battery": ("Shaver Battery", "shaver", "shaver-battery", "Shaver"),
    "Alarm System Battery": ("Alarm System Battery", "alarm system",
                             "alarm-system-battery", "Alarm System"),
    "Hotspot Battery": ("Mobile Hotspot Battery", "mobile hotspot",
                        "hotspot-battery", "Hotspot"),
    "PLC Battery": ("PLC Battery", "plc", "plc-battery", "PLC"),
    "Portable Printer Battery": ("Portable Printer Battery", "printer",
                                 "portable-printer-battery",
                                 "Portable Printer"),
    "Remote Control Battery": ("Remote Control Battery", "remote control",
                               "remote-control-battery", "Remote Control"),
    "Flashlight Battery": ("Flashlight Battery", "flashlight",
                           "flashlight-battery", "Flashlight"),
    "BabyPhone Battery": ("Baby Monitor Battery", "baby monitor",
                          "babyphone-battery", "BabyPhone"),
    "Payment Terminal Battery": ("Payment Terminal Battery",
                                 "payment terminal",
                                 "payment-terminal-battery", "Payment Terminal"),
    "CMOS / BackUp Battery": ("CMOS Backup Battery", "cmos backup",
                              "cmos-backup-battery", "CMOS / BackUp"),
    "PDA, Pocket PC Battery": ("PDA & Pocket PC Battery", "pda",
                               "pda-pocket-pc-battery", "PDA, Pocket PC"),
    "Smartwatch Battery": ("Smartwatch Battery", "smartwatch",
                           "smartwatch-battery", "Smartwatch"),
    "Thermal Camera Battery": ("Thermal Camera Battery", "thermal camera",
                               "thermal-camera-battery", "Thermal Camera"),
    "Game Console Battery": ("Game Console Battery", "game console",
                             "game-console-battery", "Game Console"),
    "Drones Battery": ("Drone Battery", "drone", "drones-battery", "Drones"),
    "Lawn Mowers Battery": ("Lawn Mower Battery", "lawn mower",
                            "lawn-mowers-battery", "Lawn Mowers"),
    "Home Security Camera Battery": ("Security Camera Battery",
                                     "security camera",
                                     "home-security-camera-battery",
                                     "Home Security Camera"),
    "Keyboard,Mouse Battery": ("Keyboard & Mouse Battery", "keyboard mouse",
                               "keyboard-mouse-battery", "Keyboard,Mouse"),
    "Remote Start and Entry Systems Battery": (
        "Remote Start Battery", "remote start",
        "remote-start-and-entry-systems-battery", None),
    "Diagnostic Scanner Battery": ("Diagnostic Scanner Battery",
                                   "diagnostic scanner",
                                   "diagnostic-scanner-battery",
                                   "Diagnostic Scanner"),
    "RAID Controller Battery": ("RAID Controller Battery", "raid controller",
                                "raid-controller-battery", "RAID Controller"),
    "Satellite Phone Battery": ("Satellite Phone Battery", "satellite phone",
                                "satellite-phone-battery", "Satellite Phone"),
    "Cable Modem Battery": ("Cable Modem Battery", "cable modem",
                            "cable-modem-battery", "Cable Modem"),
    "Remote Controller Battery": ("Remote Controller Battery",
                                  "remote controller",
                                  "drones-battery", "Remote Controller"),
    "Amplifier Battery": ("Amplifier Battery", "amplifier",
                          "amplifier-battery", "Amplifier"),
}
BAD_BRANDS = {"battery", "all", "for", "new", "oem"}
STOP = {"battery", "batteries", "pack", "for", "with", "and", "replacement",
        "packs", "series", "type", "model", "new", "oem", "compatible"}


def clean_model(m):
    words = [w for w in re.split(r"[\s/\-]+", m or "")
             if w.lower() not in STOP and len(w) > 2 and w.isascii()]
    return " ".join(words)[:40].strip()


def main():
    client = StoreService().get_client(1)
    remote, since = {}, 0
    while True:
        batch = client.request("GET", "products.json", params={
            "limit": 250, "status": "active", "since_id": since,
            "fields": "id,product_type"}).get("products", [])
        if not batch:
            break
        for p in batch:
            remote[int(p["id"])] = (p.get("product_type") or "").strip()
        since = batch[-1]["id"]
        time.sleep(0.3)
    client.close()
    cat_counts = Counter(remote.values())
    print(f"远端active={len(remote)} 分类数={len(cat_counts)}")

    brands_map = json.load(open("/tmp/cat_brands.json"))
    plans = []
    skipped = []
    for ptype, n in cat_counts.most_common():
        if ptype == "Medical Battery":
            continue
        cfg = MAP.get(ptype)
        if not cfg:
            if n >= 10:
                skipped.append((ptype, n, "无映射"))
            continue
        if n < 10:
            skipped.append((ptype, n, f"<10产品"))
            continue
        short, stem, handle, cs_cat = cfg
        brands = [b for b, _ in brands_map.get(ptype, [])
                  if b.lower() not in BAD_BRANDS][:3]
        plans.append(dict(ptype=ptype, n=n, short=short, stem=stem,
                          handle=handle, cs_cat=cs_cat, brands=brands))
    print(f"纳入 {len(plans)} 分类 | 跳过 {len(skipped)}:")
    for p, n, why in skipped:
        print(f"  SKIP {n:4} {p} ({why})")

    # device 挖词（品牌组）
    with get_cs_engine().connect() as c:
        for plan in plans:
            plan["ad_groups"] = []
            # generic 组
            stem = plan["stem"]
            generic = [
                ("PHRASE", f"replacement {stem} battery"),
                ("PHRASE", f"{stem} battery"),
                ("EXACT", f"replacement {stem} battery"),
                ("BROAD", f"buy {stem} battery"),
                ("BROAD", f"{stem} battery replacement"),
            ]
            plan["ad_groups"].append(dict(
                name=f"{plan['short']} Generic", keywords=generic))
            if not plan["cs_cat"]:
                continue
            for b in plan["brands"]:
                rows = c.execute(text(
                    "SELECT DISTINCT brand, device_model FROM device "
                    "WHERE category=:cat AND brand = :b AND brand IS NOT NULL "
                    "AND brand <> '' AND device_model IS NOT NULL "
                    "AND device_model <> '' LIMIT 60").bindparams(
                        cat=plan["cs_cat"], b=b)).fetchall()
                kws = []
                for brand, model in rows:
                    m = clean_model(model)
                    if len(m) < 3 or len(m.split()) < 1:
                        continue
                    m = m.rsplit(" ", 1)[0] if len(m.split()) > 4 else m
                    kws.append(("BROAD", f"{b} {m} battery for {stem}"))
                    kws.append(("PHRASE", f"{b} {m} battery"))
                    kws.append(("BROAD", f"{b} {m} battery"))
                    if len(kws) >= 36:
                        break
                if len(kws) >= 6:
                    plan["ad_groups"].append(dict(
                        name=f"{b} {plan['short']}", keywords=kws))

    # RSA 素材
    for plan in plans:
        short, stem = plan["short"], plan["stem"]
        b1 = plan["brands"][0] if plan["brands"] else "Top"
        b2 = plan["brands"][1] if len(plan["brands"]) > 1 else "All"
        core = short[: -len(" Battery")] if short.endswith("Battery") else short
        pool = [
            short,
            f"Replacement {core} Batteries",
            f"Battery for {b1} & {b2}",
            f"Replacement {b1} Battery",
            f"{b1} Battery Replacement",
            f"Estry {core} Batteries",
            f"Buy {core} Batteries",
            f"{core} Battery Deals",
            "US Stock, Fast Shipping",
            "1-Year Warranty Included",
            "30-Day Easy Returns",
            "Check Your Model Fit",
        ]
        heads = []
        for h in pool:
            h = h.strip()
            if h and len(h) <= 30 and h not in heads:
                heads.append(h)
        plan["headlines"] = heads[:12]
        c1 = f"{b1}, {b2} and more {stem} replacement batteries. US stock with fast shipping and 1-year warranty."
        c2 = f"Shop {stem} batteries for {b1}, {b2} and more models. Check compatibility and order today."
        c3 = "Reliable replacement batteries with 1-year warranty and 30-day returns. Ships from US warehouse."
        c4 = f"Large selection of {stem} batteries in US stock. Find your model and enjoy fast delivery."
        plan["descriptions"] = [d.strip()[:90] for d in (c1, c2, c3, c4)]
        plan["campaign"] = f"Estry {core} Search"
        plan["url"] = f"https://estrybattery.com/collections/{plan['handle']}"
        plan["path1"] = stem.replace(" ", "-")[:15]

    bad = [p["campaign"] for p in plans
           if len(p["headlines"]) < 8 or not p["ad_groups"][1:]
           and p["cs_cat"]]
    print("告警(素材<8或无品牌组):", bad or "无")
    for p in plans:
        n_kw = sum(len(g["keywords"]) for g in p["ad_groups"])
        print(f"  {p['n']:4}品 {p['campaign']:34} 组={len(p['ad_groups'])} "
              f"词={n_kw:3} 素材={len(p['headlines'])}H/{len(p['descriptions'])}D "
              f"品牌={p['brands']}")
    json.dump(plans, open("/tmp/allcat_plans.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"OK -> /tmp/allcat_plans.json ({len(plans)} campaigns)")


if __name__ == "__main__":
    main()
