# -*- coding: utf-8 -*-
"""SVG300SL 单品补图兜底：外链转存失败则下载后 base64 挂载，再不行回 draft。"""
import base64
import sys

import httpx

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

PID = "7122493702311"
URL = "https://cameronsino.co/images/CS-SVG300SL-1.jpg"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/126.0 Safari/537.36"}

r = httpx.get(URL, headers=UA, timeout=30, follow_redirects=True)
ct = r.headers.get("content-type", "?")
print(f"图库原图: HTTP {r.status_code} {ct} {len(r.content)} bytes")
cl = ShopifyRest(StoreService().get_client(1)).client

done = False
if r.status_code == 200 and len(r.content) > 1000 and "image" in ct:
    b64 = base64.b64encode(r.content).decode()
    try:
        cl.request("POST", f"products/{PID}/images.json", json_body={
            "image": {"attachment": b64, "filename": "CS-SVG300SL-1.jpg"}})
        p = cl.request("GET", f"products/{PID}.json",
                       params={"fields": "status,images"})
        print(f"base64 挂载成功: status={p['product']['status']} "
              f"images={len(p['product']['images'])}")
        done = True
    except Exception as e:  # noqa
        print(f"base64 也失败: {e}")
else:
    print("图库文件本身异常")

if not done:
    cl.request("PUT", f"products/{PID}.json", json_body={
        "product": {"id": int(PID), "status": "draft"}})
    print("回退: 已下架 draft")
