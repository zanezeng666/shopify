# -*- coding: utf-8 -*-
"""拉 wholesale 模板/B2B section/contact 表单原文。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

TID = 190031036660
rest = ShopifyRest(StoreService().get_client(1)).client
for key, out in [("templates/page.wholesale.json", "/tmp/tpl_wholesale.json"),
                 ("sections/estry-wholesale.liquid", "/tmp/sec_wholesale.liquid"),
                 ("sections/contact-form.liquid", "/tmp/sec_contact.liquid"),
                 ("templates/page.contact.json", "/tmp/tpl_contact.json")]:
    a = rest.request("GET", f"themes/{TID}/assets.json", params={"asset[key]": key})["asset"]
    open(out, "w", encoding="utf-8").write(a.get("value") or "")
    print(key, len(a.get("value") or ""))
