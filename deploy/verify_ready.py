# -*- coding: utf-8 -*-
"""全链路终验: barcode 残留/Google渠道/MPN(SKU)覆盖/vendor 分布 + MC 核对指引。"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client


def gql(q):
    r = cl._client.post(f"{cl._client.base_url}/graphql.json", auth=cl._auth,
                        json={"query": q}, timeout=60)
    return r.json()


# 1) Google & YouTube 渠道确认
r = gql("{ publications(first: 20) { nodes { name } } }")
chn = [n["name"] for n in r["data"]["publications"]["nodes"]]
print("Google & YouTube 渠道:", "存在" if any(
    "google" in n.lower() for n in chn) else "缺失!", chn and "")

# 2) 全店 barcode 残留 / vendor 分布 / SKU 覆盖
params = {"limit": 250, "status": "active", "fields": "id,vendor,variants"}
total_v = has_bc = no_sku = 0
vendors = {}
while True:
    time.sleep(0.9)
    r2 = cl._client.get("products.json", params=params, auth=cl._auth,
                        timeout=60)
    r2.raise_for_status()
    for p in r2.json()["products"]:
        vendors[p.get("vendor", "")] = vendors.get(p.get("vendor", ""), 0) + 1
        for v in p["variants"]:
            total_v += 1
            if v.get("barcode"):
                has_bc += 1
            if not v.get("sku"):
                no_sku += 1
    link = r2.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1],
              "fields": "id,vendor,variants"}

print(f"变体总数: {total_v}")
print(f"barcode 残留: {has_bc}  (目标 0)")
print(f"无 SKU(无MPN)变体: {no_sku}")
print(f"vendor 分布: {vendors}")

print("""
================ MC 后台核对指引 ================
1. 打开 merchantcenter.google.com -> 产品 -> 全部
   - 预期: 24-48h 内 '产品标识符不正确' 类被拒项归零(新同步生效后)
   - 顶部诊断: 账号问题/商品问题 两栏查看
2. 若仍有被拒, 截图给 AI 助手逐项分析
3. 恢复正常后即可创建 Performance Max campaign
=================================================""")
