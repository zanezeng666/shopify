# -*- coding: utf-8 -*-
"""回退 zebra 试点: 删除插入的规格表段, 恢复原描述并校验。"""
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
HANDLE = ("battery-for-zebra-zr138-zr138cr-p1098850-00-p1098850-01-"
          "p1098850-002")

r = cl._client.get("products.json", params={
    "limit": 1, "handle": HANDLE, "fields": "id,handle,body_html"},
    auth=cl._auth)
p = r.json()["products"][0]
body = p["body_html"] or ""
print("回退前长度:", len(body))

pat = re.compile(
    r'<div style="margin:0 0 8px;font-size:16px;font-weight:700;'
    r'color:#1B2A41;">Battery Specifications</div>.*?'
    r'<div style="font-size:13px;color:#5A6B7F;margin:0 0 18px;">'
    r'Category:.*?</div>', re.S)
nb, n = pat.subn("", body)
if n != 1:
    print(f"匹配 {n} 段, 异常中止不写入")
    sys.exit(1)
print("删除字符数:", len(body) - len(nb), "回退后长度:", len(nb))

r = cl._client.put(f"products/{p['id']}.json", auth=cl._auth,
                   json={"product": {"id": p["id"], "body_html": nb}})
r.raise_for_status()
print("已恢复原描述 ✓")
