# -*- coding: utf-8 -*-
"""v2.2 全量刷：body + options(Capacity) + seo.description + 图片 alt。

范围：created_at >= 2026-10-30 的 4510 个自建产品。
用法:
  python refresh_all_v22.py --limit 3   # 试运行 3 个
  python refresh_all_v22.py             # 全量（断点续跑，进度文件 refresh_all.done）
幂等：body/options/metafield/alt 均确定性重算，重跑无副作用。
速率：~0.35s/请求（client 另有 429 指数退避），4510 品约 1 小时。
"""
import json
import re
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.products.sync_shopify import CsShopifySyncService as S
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

CS_RE = re.compile(r"^CS-([A-Z0-9]+)_", re.I)
LIMIT = next((int(a.split("=")[1]) for a in sys.argv[1:] if a.startswith("--limit=")), 0)
DONE = "/home/jason/shopify-admin/deploy/refresh_all.done"
SKIP = "/home/jason/shopify-admin/deploy/refresh_all.skip"

svc = S()
catalog = svc.load_cs_catalog()
client = StoreService().get_client(1)
rest = ShopifyRest(client)
cl = rest.client

done_ids = set()
try:
    with open(DONE) as f:
        done_ids = {int(x) for x in f.read().split() if x.strip()}
except FileNotFoundError:
    pass
print(f"进度: 已完成 {len(done_ids)}，catalog {len(catalog)}", flush=True)


def page_products():
    params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
              "fields": "id,title,sku,options,images,variants"}
    path = "products.json"
    while True:
        r = cl._client.get(path, params=params, auth=cl._auth)
        r.raise_for_status()
        for p in r.json()["products"]:
            yield p
        link = r.headers.get("Link", "")
        nxt = [x.split(";")[0].strip("<>") for x in link.split(",")
               if 'rel="next"' in x]
        if not nxt:
            return
        params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}


def find_row(sku):
    m = CS_RE.match(sku or "")
    if not m:
        return None
    csid = "CS-" + m.group(1).upper()
    seg = sku.split("_")[1].lower() if sku.count("_") >= 2 else ""
    rows = [(str(bl).lower(), r) for (c, bl), r in catalog.items()
            if str(c).upper() == csid]
    if not rows:
        return None
    return next((r for bl, r in rows if bl == seg), rows[0][1])


n_ok = n_skip = n_upd = 0
t0 = time.time()
for p in page_products():
    if LIMIT and n_ok >= LIMIT:
        break
    pid = p["id"]
    if pid in done_ids:
        continue
    sku = (p.get("variants") or [{}])[0].get("sku", "")
    row = find_row(sku)
    if row is None:
        with open(SKIP, "a") as f:
            f.write(f"{pid}\t{sku}\n")
        n_skip += 1
        continue
    title = p["title"]
    payload = {"id": pid, "body_html": S._build_body_html(row),
               "options": [{"name": "Capacity"}]}
    imgs = [{"id": im["id"],
             "alt": title if i == 0 else f"{title} - {i + 1}"}
            for i, im in enumerate(p.get("images") or [])]
    if imgs:
        payload["images"] = imgs
    try:
        rest.update_product(pid, payload)
        time.sleep(0.2)
        cl.request("POST", f"products/{pid}/metafields.json", json_body={
            "metafield": {"namespace": "seo", "key": "description",
                          "value": S._entity_text(row)[:155],
                          "type": "single_line_text_field"}})
        with open(DONE, "a") as f:
            f.write(f"{pid}\n")
        done_ids.add(pid)
        n_ok += 1
    except Exception as e:
        print(f"ERR {pid} {sku[:28]}: {str(e)[:140]}", flush=True)
    n_upd += 1
    if n_upd % 50 == 0:
        rate = n_upd / max(time.time() - t0, 1)
        eta = (len(done_ids) and int((4510 - len(done_ids)) / max(rate, 0.01) / 60)) or 0
        print(f"... {n_upd} 处理 / {len(done_ids)} 完成 / {n_skip} 跳过 "
              f"| {rate:.2f} 品/s | ETA {eta}min", flush=True)
    time.sleep(0.15)

client.close()
print(f"== 结束: 完成 {n_ok} 累计 {len(done_ids)} / 跳过 {n_skip} "
      f"/ 用时 {(time.time() - t0) / 60:.1f}min", flush=True)
