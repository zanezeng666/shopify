# -*- coding: utf-8 -*-
"""20个露码/露CS-QR主图的产品: 全图扫描 -> 干净图置顶(不删图, 保序)。"""
import io
import sys
import time

import httpx
import zxingcpp
from PIL import Image

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
HC = httpx.Client(timeout=20, follow_redirects=True)

BAD_PID = [15484822978804, 15484990685428, 15485293592820, 15485343138036,
           15485451993332, 15485467492596, 15485471228148, 15485522149620,
           15485522215156, 15485522378996, 15485522542836, 15485522608372,
           15485607772404, 15485526933748, 4640846184548, 4641007730788,
           4641146765412, 7119427502247, 7122779209895, 7124242596007]


def dirty(img):
    img = img.convert("RGB")
    if img.width > 1200:
        img = img.resize((1200, int(img.height * 1200 / img.width)))
    for x in zxingcpp.read_barcodes(img):
        f = x.format.name
        if f in ("EAN13", "UPCA", "EAN8", "UPCE"):
            return True
        if f == "QRCode" and "cameronsino" in x.text.lower():
            return True
    return False


report = []
for pid in BAD_PID:
    try:
        time.sleep(0.5)
        r = cl._client.get(f"products/{pid}.json", auth=cl._auth,
                           params={"fields": "id,title,images"})
        r.raise_for_status()
        p = r.json()["product"]
        imgs = p["images"]
        flags = []
        for im in imgs:
            try:
                b = HC.get(im["src"]).content
                flags.append(dirty(Image.open(io.BytesIO(b))))
            except Exception:
                flags.append(False)
        clean_idx = next((i for i, d in enumerate(flags) if not d), None)
        if clean_idx is None:
            report.append((pid, f"ALL_DIRTY({len(imgs)}图)", p["title"][:40]))
            print(f"{pid} ALL_DIRTY {flags}", flush=True)
            continue
        if clean_idx == 0:
            report.append((pid, "ALREADY_CLEAN_TOP", p["title"][:40]))
            continue
        order = [imgs[clean_idx]] + [im for i, im in enumerate(imgs)
                                     if i != clean_idx]
        time.sleep(0.5)
        r2 = cl._client.put(
            f"products/{pid}.json", auth=cl._auth,
            json={"product": {"id": pid,
                              "images": [{"id": im["id"]} for im in order]}})
        ok = r2.status_code == 200
        report.append((pid, f"REORDER {clean_idx}->0 {'OK' if ok else 'FAIL'}",
                       p["title"][:40]))
        print(f"{pid} REORDER {clean_idx}->0 {'OK' if ok else r2.status_code}",
              flush=True)
    except Exception as ex:
        report.append((pid, f"ERROR {str(ex)[:60]}", ""))
        print(f"{pid} ERROR {str(ex)[:80]}", flush=True)

print("\n=== 整改报告 ===")
for row in report:
    print(" ", row)
