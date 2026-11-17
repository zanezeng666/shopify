"""Dawn 预览基线（容错版）：draft previewUrl 叠加 preview_theme_id 后的渲染断言。"""
import json
import re
import subprocess
import sys
import traceback

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

TID = 190031036660
PID = 15476051902708
c = ShopifyRest(StoreService().get_client(1)).client

try:
    d = c.graphql("query($id: ID!){ product(id: $id){ productPreviewUrl } }",
                  {"id": f"gid://shopify/Product/{PID}"})
    u = (d.get("product") or {}).get("productPreviewUrl")
    print("graphql ok | previewUrl:", (u or "NONE")[:120])
except Exception:
    traceback.print_exc()
    sys.exit(1)

full = u + ("&" if "?" in u else "?") + f"preview_theme_id={TID}"
try:
    r = subprocess.run(["curl", "-skL", "-m", "60", "-w", "\n%{http_code}", full],
                       capture_output=True, text=True, timeout=75)
    body, _, code = r.stdout.rpartition("\n")
    print("dawn draft preview:", code, len(body), "B")
    print("  spec-table:", "Specification</h3>" in body,
          "| FAQ details:", "<details" in body,
          "| entity:", "This is a" in body)
    print("  ld+json blocks:", body.count("application/ld+json"))
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', body, re.S):
        try:
            j = json.loads(m.group(1))
            print("  ld:", j.get("@type"), "| name:", str(j.get("name", ""))[:44])
        except Exception as e:
            print("  ld parse fail:", str(e)[:70])
    with open("/tmp/dawn_prod.html", "w", encoding="utf-8") as f:
        f.write(body)
except Exception:
    traceback.print_exc()

r = subprocess.run(["curl", "-skL", "-m", "40", "-o", "/dev/null", "-w",
                    "%{http_code} -> %{url_effective}",
                    f"https://www.estrybattery.com/?preview_theme_id={TID}"],
                   capture_output=True, text=True, timeout=50)
print("preview home:", r.stdout[:170])
