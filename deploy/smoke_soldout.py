# -*- coding: utf-8 -*-
"""线上冒烟：容量顺序 + 可购状态（产品 .js JSON）。"""
import json
import urllib.request

HANDLES = [
    "battery-for-al-ko-comfort-gt-1825-comfort-ps-181-comfort-hta-1845-comfort-ps-1815-comfort-ht-1845-co",
    "battery-for-sichler-reinigungs-roboter-pcr-1350-l-pcr-2350-lx-nc-3337-nc-3338-pcr-3350",
    "battery-for-dewalt-20v-max-60v-max-120v-max-dcb184-dcb184-xj-dcb184-xr-dcd740-dcd740b-dcd780-dcd780b",
    "battery-for-dolmar-ah-3756-xe3-ah1853h-ah3766x3-ah-3766-xe3-ag-3729-ag-3750-ah-3756-ah-3766-as-1813",
]
for h in HANDLES:
    with urllib.request.urlopen(
            f"https://estrybattery.com/products/{h}.js", timeout=30) as r:
        d = json.load(r)
    vs = d.get("variants", [])
    seq = [v["public_title"] or v["option1"] for v in vs]
    avail = [v.get("available") for v in vs]
    bad = [seq[i] for i, a in enumerate(avail) if not a]
    mark = "OK " if not bad else "SOLDOUT!"
    print(f"{mark} {h[:45]}")
    print(f"     顺序={seq} 可购={avail}")
