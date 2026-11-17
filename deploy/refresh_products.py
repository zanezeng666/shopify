# -*- coding: utf-8 -*-
"""线上产品信息全量刷新（CS 最新数据 + v2 模板 + vendor 切 Estry）。

流程：分页拉 ACTIVE 产品 → SKU 锚定 CS 记录 → v2 渲染 diff
→ productUpdate（title/bodyHtml/productType/vendor）
→ productVariantsBulkUpdate（仅补空 barcode）
不动：handle/tags/price/images/SEO/已有 barcode。
用法：
  试推验证:  python refresh_products.py 30
  全量 nohup: nohup python refresh_products.py 0 > /tmp/refresh_products.log 2>&1 &
断点: /tmp/refresh_done.txt（已推 product numeric id，每 50 个落盘）。
"""
import json
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from loguru import logger

from shopify_admin.services.products.sync_shopify import (
    CsShopifySyncService, _CS_ID_RE,
)
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

logger.remove()
logger.add(sys.stderr, level="INFO")

LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 30   # 0 = 全量
DONE_FILE = "/tmp/refresh_done.txt"

svc = CsShopifySyncService()
client = ShopifyRest(StoreService().get_client(1)).client

catalog = svc.load_cs_catalog()
on_sale = {k: v for k, v in catalog.items() if v["status"] == 1}
by_cs: dict[str, list[str]] = {}
for (csid, bl) in catalog:
    by_cs.setdefault(csid, []).append(bl)
logger.info(f"CS 目录 records={len(catalog)} on_sale={len(on_sale)}")

try:
    done = {int(x) for x in open(DONE_FILE).read().split()}
except Exception:
    done = set()
logger.info(f"断点已推 {len(done)} 个")


def match_cs(vs):
    """返回 (cs_row, None) 或 (None, 原因)。"""
    sku = (vs[0]["sku"] or "").strip() if vs else ""
    m = _CS_ID_RE.match(sku)
    if not m or not vs:
        return None, "unanchored"
    csid = m.group(1)
    parts = sku.split("_")
    bseg = parts[1].lower() if len(parts) >= 2 else ""
    recs = by_cs.get(csid) or []
    if not recs:
        return None, "nomatch"
    bl = bseg if bseg in recs else (recs[0] if len(recs) == 1 else None)
    if bl is None:
        return None, "brand_mismatch"
    cs = on_sale.get((csid, bl))
    if cs is None:
        return None, "stopped"
    return cs, None


Q = """
{
  products(first: 250, sortKey: CREATED_AT, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    nodes {
      id title handle productType vendor
      bodyHtml
      variants(first: 10) {
        nodes { id sku barcode
          inventoryItem { measurement { weight { value unit } } } }
      }
    }
  }
}"""

MUT = """
mutation PU($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id }
    userErrors { field message }
  }
}"""

MUT_V = """
mutation PV($pid: ID!, $vs: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $pid, variants: $vs) {
    productVariants { id }
    userErrors { field message }
  }
}"""


def numeric_id(gid: str) -> int:
    return int(gid.rsplit("/", 1)[-1])


# ---- 阶段 1：拉全量 + 渲染 diff ----
tasks: list[dict] = []
stat = dict(total=0, skip_unanchored=0, skip_nomatch=0, skip_brand=0, skip_stopped=0,
            skipped_done=0, need_update=0, clean=0, barcode_fill=0)
cursor = None
pages = 0
t0 = time.monotonic()
while True:
    qq = Q.replace("(first: 250,", '(first: 250, after: "%s",' % cursor) if cursor else Q
    r = client.graphql(qq)
    pages += 1
    conn = r["products"]
    for p in conn["nodes"]:
        stat["total"] += 1
        pid_num = numeric_id(p["id"])
        if pid_num in done:
            stat["skipped_done"] += 1
            continue
        cs, why = match_cs(p["variants"]["nodes"])
        if cs is None:
            stat[f"skip_{why}" if why != "unanchored" else "skip_unanchored"] = \
                stat.get(f"skip_{why}", 0) + 1
            continue
        pay = svc.build_new_product_payload(cs)
        input_: dict = {"id": p["id"]}
        if p["title"] != pay["title"]:
            input_["title"] = pay["title"]
        if (p["bodyHtml"] or "") != pay["body_html"]:
            input_["descriptionHtml"] = pay["body_html"]
        if (p["productType"] or "") != pay["product_type"]:
            input_["productType"] = pay["product_type"]
        if (p["vendor"] or "") != pay["vendor"]:
            input_["vendor"] = pay["vendor"]
        # 变体：仅补空 barcode（重量实证零漂移不动）
        vfix = []
        src_bar = (cs["bar_code"] or "").strip()
        for v in p["variants"]["nodes"]:
            if src_bar and not (v["barcode"] or "").strip():
                vfix.append({"id": v["id"], "barcode": src_bar})
        if len(input_) == 1 and not vfix:
            stat["clean"] += 1
            continue
        stat["need_update"] += 1
        if vfix:
            stat["barcode_fill"] += len(vfix)
        tasks.append({"pid": p["id"], "pid_num": pid_num, "handle": p["handle"],
                      "input": input_ if len(input_) > 1 else None, "vfix": vfix})
    cursor = conn["pageInfo"]["endCursor"]
    logger.info(f"拉取 {pages} 页，累计 total={stat['total']} need_update={len(tasks)}")
    if not conn["pageInfo"]["hasNextPage"]:
        break

logger.info(f"拉取完成 ({time.monotonic()-t0:.0f}s): {stat}")

if LIMIT:
    tasks = tasks[:LIMIT]
    logger.info(f"试推模式：截取前 {len(tasks)} 个")

# ---- 阶段 2：推送 ----
ok_n = err_n = 0
consec_fail = 0
t1 = time.monotonic()
done_f = open(DONE_FILE, "a", encoding="utf-8")
err_log = open("/tmp/refresh_errors.log", "a", encoding="utf-8")
for i, tk in enumerate(tasks, 1):
    try:
        prod_ok = True
        if tk["input"]:
            r = client.graphql(MUT, {"input": tk["input"]})
            ue = r["productUpdate"]["userErrors"]
            if ue:
                prod_ok = False
                err_n += 1
                consec_fail += 1
                err_log.write(f"{tk['pid']} productUpdate: {ue}\n")
            else:
                ok_n += 1
                consec_fail = 0
        if prod_ok and tk["vfix"]:
            r = client.graphql(MUT_V, {"pid": tk["pid"], "vs": tk["vfix"]})
            ue = r["productVariantsBulkUpdate"]["userErrors"]
            if ue:
                err_log.write(f"{tk['pid']} variants: {ue}\n")
            else:
                ok_n += 1
        if prod_ok:
            done_f.write(f"{tk['pid_num']}\n")
            if (i % 50 == 0) or (i % 20 == 0 and i <= 60):
                done_f.flush()
    except Exception as e:  # noqa: BLE001
        err_n += 1
        consec_fail += 1
        err_log.write(f"{tk['pid']} EXC: {str(e)[:200]}\n")
        if consec_fail >= 30:
            logger.error(f"连续 {consec_fail} 失败熔断中止（已推 {i-1}）")
            break
    if i % 200 == 0:
        rate = i / (time.monotonic() - t1)
        logger.info(f"推送 {i}/{len(tasks)} ({rate:.1f}/s) ok={ok_n} err={err_n}")

done_f.close()
err_log.close()
logger.info(f"DONE ok={ok_n} err={err_n} 耗时 {time.monotonic()-t1:.0f}s "
            f"（done 总数 {len(done)+len(tasks)}）")
