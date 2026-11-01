# -*- coding: utf-8 -*-
"""真数据冒烟：本地起 TestClient，连真实 cs_new 费率表跑回调与试算。"""
from loguru import logger

logger.remove()

from fastapi.testclient import TestClient  # noqa: E402

from shopify_admin.api.app import create_app  # noqa: E402

c = TestClient(create_app())

# 1) 模拟 Shopify 结账回调（270g 电池×2 → 540g，加州 90001）
payload = {"rate": {
    "items": [{"sku": "CS-TVR500VX_Brand_27_0", "quantity": 2, "grams": 270}],
    "destination": {"country": "US", "postal_code": "90001"},
}}
r = c.post("/shopify/callback/carrier-rates", json=payload)
print("callback:", r.status_code, r.json())
assert r.status_code == 200 and r.json()["rates"], "回调无报价"

# 2) 模拟 grams 缺失回退查库（sku → cs_id → cs_product 重量）
payload2 = {"rate": {
    "items": [{"sku": "CS-TVR500VX_Brand_27_0", "quantity": 1}],
    "destination": {"country": "US", "postal_code": "10001"},
}}
r2 = c.post("/shopify/callback/carrier-rates", json=payload2)
print("fallback:", r2.status_code, r2.json())

# 3) 非美国目的地 → 空 rates
r3 = c.post("/shopify/callback/carrier-rates", json={"rate": {
    "items": payload["rate"]["items"],
    "destination": {"country": "CA", "postal_code": "M5V"},
}})
print("non-us:", r3.status_code, r3.json())
assert r3.json() == {"rates": []}
print("\nOK")
