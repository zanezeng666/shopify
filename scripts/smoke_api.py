# -*- coding: utf-8 -*-
"""REST 层冒烟：app 可导入、路由齐全、鉴权/错误结构正常。"""
from fastapi.testclient import TestClient

from shopify_admin.api.app import app

client = TestClient(app)

# 路由清单以 OpenAPI 为准（新 FastAPI include_router 延迟展平，app.routes 不可直接枚举）
paths = client.get("/openapi.json").json()["paths"]
n_ops = sum(len(v) for v in paths.values())
print(f"OPENAPI paths={len(paths)} operations={n_ops}")
for p in sorted(paths):
    print(f"  {sorted(m.upper() for m in paths[p])} {p}")

r = client.get("/health")
assert r.status_code == 200, r.text
print("health:", r.json())

# API_KEYS 未配置时为无鉴权模式（本地调试），业务接口直接可读
r = client.get("/stores")
print("no-key /stores ->", r.status_code, r.json())
assert r.status_code == 200, r.text

# 404 统一错误结构
r = client.get("/orders/999999")
print("missing order ->", r.status_code, r.json())
assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"

print("SMOKE OK")
