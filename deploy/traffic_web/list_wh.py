"""列仓库+渠道时效；然后配路由+触发 job。"""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8002/api/v1"
KEY = "WnNboEJ8MQXU0z1e5u6ZrVkA9hLR2lwB4GIjpyca"


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method,
                                 headers={"X-Admin-Key": KEY,
                                          "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body else None)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:300]}


if sys.argv[1] == "--wh":
    d = call("GET", "/admin/logistics")
    for w in d.get("warehouses", []):
        ships = [f"{s['carrier_code']}:{s['min_days']}-{s['max_days']}d"
                 for s in w.get("shippings", [])]
        print(f"{w['supplier_code']}/{w['warehouse_code']} {w['name']} "
              f"[{w['status']}] {ships}")
elif sys.argv[1] == "--routes":
    ROUTES = [
        {"supplier": "cs", "warehouse": "US", "dest_country": "US",
         "priority": 10, "name": "美国仓优先(USPS 2-5天)", "ship_method": ""},
        {"supplier": "hy", "warehouse": "SZ", "ship_method": "CSUSPS",
         "dest_country": "US", "priority": 15,
         "name": "美国回落深圳CS-USPS(8-15天)"},
        {"supplier": "cs", "warehouse": "SZ", "ship_method": "OGL",
         "dest_country": "RU", "priority": 20, "name": "俄罗斯OGL(13-30天)"},
        {"supplier": "cs", "warehouse": "SZ", "ship_method": "ZT",
         "dest_country": "", "priority": 100,
         "name": "全球兜底深圳ZT(21-35天)"},
    ]
    for r in ROUTES:
        out = call("POST", "/admin/platforms/shopify/routes", r)
        print(("OK " if "http_error" not in out else "ERR "),
              r["name"], json.dumps(out, ensure_ascii=False)[:200])
    print(json.dumps(call("GET", "/admin/platforms/shopify/routes"),
                     ensure_ascii=False)[:800])
elif sys.argv[1] == "--jobs":
    for code in ("sync_cs_inventory", "shopify_inventory_push"):
        out = call("POST", f"/admin/jobs/{code}/run")
        print(code, json.dumps(out, ensure_ascii=False)[:250])
