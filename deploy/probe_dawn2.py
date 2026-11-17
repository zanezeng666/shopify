"""Dawn 副本补充探测：settings 颜色结构 / draft 产品在 Dawn 预览下的渲染基线。只读。"""
import json
import re
import subprocess
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

TID = 190031036660
PID = 15476051902708  # iHome 样例
c = ShopifyRest(StoreService().get_client(1)).client

# 1) settings_data current 结构
v = c.request("GET", f"themes/{TID}/assets.json",
              params={"asset[key]": "config/settings_data.json"})["asset"]["value"]
cur = json.loads(v).get("current", {})
print("current keys:", sorted(cur.keys())[:40], "...")
cs = cur.get("color_schemes")
if isinstance(cs, dict):
    print("scheme ids:", list(cs.keys()))
    for sid, sv in list(cs.items())[:2]:
        print(f"  {sid}:", sv.get("settings"))
else:
    print("no color_schemes; color-ish keys:", [k for k in cur if "color" in k.lower()])
print("font keys:", {k: cur[k] for k in cur if k.startswith("type_")})

# 2) draft previewUrl + 叠加 preview_theme_id（Dawn 预览基线）
d = c.graphql("query($id: ID!){ product(id: $id){ productPreviewUrl } }",
              {"id": f"gid://shopify/Product/{PID}"})
u = (d.get("product") or {}).get("productPreviewUrl")
print("previewUrl:", (u or "NONE")[:110])
if u:
    full = u + ("&" if "?" in u else "?") + f"preview_theme_id={TID}"
    r = subprocess.run(["curl", "-skL", "-w", "\n%{http_code}", full],
                       capture_output=True, text=True, timeout=90)
    body, _, code = r.stdout.rpartition("\n")
    print("dawn draft preview:", code, len(body), "B")
    print("  spec-table:", "Specification</h3>" in body,
          "| FAQ details:", "<details" in body,
          "| entity sentence:", "This is a" in body)
    print("  ld+json blocks:", body.count("application/ld+json"))
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', body, re.S):
        try:
            j = json.loads(m.group(1))
            print("  ld type:", j.get("@type"), "| name:", str(j.get("name", ""))[:44])
        except Exception as e:
            print("  ld parse fail:", str(e)[:60])
    with open("/tmp/dawn_prod.html", "w", encoding="utf-8") as f:
        f.write(body)

# 3) 主页预览 302 跟随终态
r = subprocess.run(["curl", "-skL", "-o", "/dev/null", "-w",
                    "%{http_code} -> %{url_effective}",
                    f"https://www.estrybattery.com/?preview_theme_id={TID}"],
                   capture_output=True, text=True, timeout=60)
print("preview home:", r.stdout[:170])
