"""Estry 店（Bangmi 主体唯一自营店，store 1）全链体检 2026-11-09。只打印状态与计数，不打印密钥。"""
import os
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

ENV = "/home/jason/shopify-admin/.env"


def load_env(path: str) -> dict:
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
            if m:
                out[m.group(1)] = m.group(2)
    return out


os.environ.update(load_env(ENV))
env = os.environ

import httpx  # noqa: E402
import pymysql  # noqa: E402


def conn(prefix: str, db: str | None = None):
    return pymysql.connect(
        host=env[f"{prefix}_HOST"], port=int(env.get(f"{prefix}_PORT", "3306")),
        user=env[f"{prefix}_USER"], password=env[f"{prefix}_PASSWORD"],
        database=db or env[f"{prefix}_NAME"], charset="utf8mb4",
        connect_timeout=15, cursorclass=pymysql.cursors.DictCursor,
    )


print("== 1) stores 表与核心数据规模 ==")
with conn("SHOPIFY_DB") as c, c.cursor() as cur:
    cur.execute(
        "SELECT id, username, domain, primary_domain, is_available,"
        " is_inventory_available, rcustomerno FROM stores"
    )
    for r in cur.fetchall():
        print("store:", r)
    cur.execute("SHOW TABLES")
    tables = [list(r.values())[0] for r in cur.fetchall()]
    print("tables:", tables)
    for t in ("products", "product_variants", "orders", "inventory_sync_logs",
              "prices", "price_records", "sync_logs"):
        if t not in tables:
            continue
        cur.execute(f"SELECT COUNT(*) AS n FROM {t}")
        n = cur.fetchone()["n"]
        cur.execute(f"SHOW COLUMNS FROM {t}")
        cols = [x["Field"] for x in cur.fetchall()]
        pick = next((x for x in ("created_at", "updated_at", "synced_at") if x in cols), None)
        extra = ""
        if pick:
            cur.execute(f"SELECT MAX({pick}) AS m FROM {t}")
            extra = f"  max({pick})={cur.fetchone()['m']}"
        print(f"[{t}] rows={n}{extra}")

print("\n== 2) Shopify REST 连通性（get_client(1).verify()）==")
from shopify_admin.services.stores.service import StoreService  # noqa: E402

svc = StoreService()
with svc.get_client(1) as cl:
    shop = cl.verify()
    print({k: shop.get(k) for k in ("id", "name", "domain", "myshopify_domain",
                                    "primary_domain", "currency", "timezone")})

print("\n== 3) shopify_admin API（8100）健康 ==")
try:
    r = httpx.get("http://127.0.0.1:8100/health", timeout=10)
    print("health:", r.status_code, r.text[:200])
except Exception as e:  # noqa: BLE001
    print("health err:", e)

print("\n== 4) BMAI cs-api 对接（CS_API_BASE/CS_API_KEY）==")
base = env.get("CS_API_BASE") or env.get("CS_API_BASE_URL") or ""
key = env.get("CS_API_KEY", "")
print("CS_API_BASE=", base, " key set:", bool(key))
if base:
    try:
        r = httpx.get(base.rstrip("/") + "/health", timeout=10)
        print("bmai-cs-api health:", r.status_code, r.text[:120])
    except Exception as e:  # noqa: BLE001
        print("bmai-cs-api health err:", e)

print("\n== 5) supply-chain 平台 API（sc_hub.platform shopify key）==")
try:
    with conn("CS_DB", db="sc_hub") as c, c.cursor() as cur:
        cur.execute("SELECT id, code, status FROM platform")
        print("platform rows:", cur.fetchall())
        cur.execute("SELECT api_key FROM platform WHERE code='shopify' AND status='active'")
        row = cur.fetchone()
    sk = row["api_key"] if row else None
    if sk:
        with httpx.Client(base_url="http://127.0.0.1:8002",
                          headers={"X-API-Key": sk}, timeout=90) as api:
            r = api.get("/api/v1/suppliers")
            print("[suppliers]", r.status_code,
                  [s["code"] for s in r.json().get("items", [])])
            r = api.get("/api/v1/inventory/overview", params={"supplier": "cs"})
            print("[cs overview]", r.status_code, "skus:", len(r.json().get("totals", {})))
    else:
        print("no active shopify platform key")
except Exception as e:  # noqa: BLE001
    print("supply-chain probe err:", repr(e))
