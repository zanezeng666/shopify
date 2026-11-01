# -*- coding: utf-8 -*-
"""端到端冒烟: apply 挂外链图建 draft → 回读店铺验证图片转存 cdn.shopify.com"""
import sys

from loguru import logger

logger.remove()

from shopify_admin.services.products.sync_shopify import CsShopifySyncService  # noqa: E402

CS_ID = sys.argv[1] if len(sys.argv) > 1 else ""

svc = CsShopifySyncService()

# 0) 无指定时从 to_create 样本自动挑一个图库有图的
d = svc.diff(1)
if not CS_ID:
    import httpx  # noqa: E402
    from shopify_admin.services.products.sync_shopify import (  # noqa: E402
        _CS_IMG_HEADERS, cs_image_urls,
    )
    with httpx.Client(timeout=10, follow_redirects=True,
                      headers=_CS_IMG_HEADERS) as h:
        for i in d["plan"]["to_create"]["items"]:
            if cs_image_urls(i["cs_id"], lambda u: h.head(u).status_code == 200):
                CS_ID = i["cs_id"]
                break
    print("auto-picked:", CS_ID)
    if not CS_ID:
        sys.exit("样本内无图库命中")

# 1) 确认在 to_create 计划内
d = svc.diff(1)
hit = [i for i in d["plan"]["to_create"]["items"] if i["cs_id"] == CS_ID]
print(f"diff to_create={d['plan']['to_create']['count']}, {CS_ID} in plan: {bool(hit)}")
if not hit:
    sys.exit(1)

# 2) 图库探测（真网络，验证探测通路与张数）
import httpx  # noqa: E402
from shopify_admin.services.products.sync_shopify import (  # noqa: E402
    _CS_IMG_HEADERS, cs_image_urls,
)

with httpx.Client(timeout=10, follow_redirects=True, headers=_CS_IMG_HEADERS) as h:
    urls = cs_image_urls(
        CS_ID, lambda u: h.head(u).status_code == 200)
print(f"probe {CS_ID}: {len(urls)} imgs, first={urls[0] if urls else None}")

# 3) apply 单点建 draft（幂等: handle 已存在则 skip）
r = svc.apply(1, dry_run=False, publish_status="draft", only_cs_id=CS_ID)
print("apply:", {k: r[k] for k in
                 ("created", "skipped_existing", "failed",
                  "images_attached", "images_missing", "errors")})

# 4) 回读店铺，验证图片已转存 cdn.shopify.com
from sqlalchemy import text  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

client = StoreService().get_client(1)
try:
    rest = ShopifyRest(client)
    handle = [i for i in d["plan"]["to_create"]["items"]
              if i["cs_id"] == CS_ID][0]["handle"]
    p = rest.product_by_handle(handle)
    if not p:
        print("!! 店铺未取到产品", handle)
        sys.exit(1)
    p = client.request("GET", f"products/{p['id']}.json").get("product", p)
    imgs = p.get("images") or []
    print(f"store product {p['id']} images={len(imgs)}")
    for i in imgs[:3]:
        print("  ", i.get("src"))
    dom_ok = all(str(i.get("src", "")).startswith("https://cdn.shopify.com/") for i in imgs)
    print("all on cdn.shopify.com:", dom_ok)
    print("store imgs == probe imgs:", len(imgs) == len(urls))
finally:
    client.close()
