# -*- coding: utf-8 -*-
"""医疗广告品打标: tag ad-medical + metafield custom_label_0 (不改价格)。
价格体系维持现状(用户拍板以量为主)。幂等可重跑。
前置: 清码完成 (verify_ready.log 存在, 避免限流互挤)。
输出: deploy/ad_ready_applied.json。
"""
import json
import os
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

DEP = "/home/jason/shopify-admin/deploy"
SRC = f"{DEP}/ad_medical_selected.json"
ARC = f"{DEP}/ad_ready_applied.json"
MARK = f"{DEP}/verify_ready.log"     # 清码完成标记

if not os.path.exists(MARK):
    print("清码未完成(无 verify_ready.log), 稍后再跑")
    sys.exit(1)

data = json.load(open(SRC, encoding="utf-8"))
sel = data["selected"]
done = set()
if os.path.exists(ARC):
    done = {x["product_id"] for x in json.load(
        open(ARC, encoding="utf-8"))["applied"]}
todo = [x for x in sel if x["product_id"] not in done]
print(f"selected={len(sel)} 已完成={len(done)} 待处理={len(todo)}")

cl = ShopifyRest(StoreService().get_client(1)).client
applied = [] if not os.path.exists(ARC) else json.load(
    open(ARC, encoding="utf-8"))["applied"]
t0 = time.time()
fail = 0

for i, d in enumerate(todo):
    pid = d["product_id"]
    ok = False
    for attempt in range(3):
        try:
            r = cl._client.get(f"products/{pid}.json", auth=cl._auth,
                               params={"fields": "id,tags"}, timeout=30)
            p = r.json()["product"]
            tags = [t for t in (p.get("tags") or "").split(",") if t]
            if "ad-medical" in tags:
                ok = True            # 已打过, 幂等跳过
                break
            tags.append("ad-medical")
            body = {"product": {
                "id": pid, "tags": ",".join(tags),
                "metafields": [{
                    "namespace": "google_shopping",
                    "key": "custom_label_0",
                    "type": "single_line_text_field",
                    "value": "ad-medical"}],
            }}
            r2 = cl._client.put(f"products/{pid}.json", auth=cl._auth,
                                json=body, timeout=30)
            if r2.status_code == 200:
                ok = True
                break
            print(f"  HTTP{r2.status_code} @{pid} {r2.text[:70]}")
        except Exception as e:
            print(f"  EXC @{pid}: {type(e).__name__} {str(e)[:60]}")
        time.sleep(1.5 * (attempt + 1))
    if ok:
        applied.append({"product_id": pid, "title": d["title"],
                        "cs_id": d["cs_id"], "price": d["price"],
                        "amzn_ref": d["amzn_ref"],
                        "stock_total": d["stock_total"]})
    else:
        fail += 1
        print(f"  FAIL @{pid} {d['title'][:40]}")
    time.sleep(0.5)
    if (i + 1) % 25 == 0:
        json.dump({"applied": applied},
                  open(ARC, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"  [{i + 1}/{len(todo)}] 已用 {int(time.time() - t0)}s")

json.dump({"applied": applied}, open(ARC, "w", encoding="utf-8"),
          ensure_ascii=False)
print(f"完成: {len(applied)}/{len(sel)} 打标(价格未动); "
      f"失败 {fail}; 档案 {ARC}")
