"""探测 ESTRY Dawn v16 副本（id 190031036660）：元信息/资产/自带 schema/settings/预览基线。只读。"""
import json
import re
import subprocess
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

TID = 190031036660
c = ShopifyRest(StoreService().get_client(1)).client

# 1) 主题元信息
t = c.request("GET", f"themes/{TID}.json")["theme"]
print("theme:", t["id"], "|", t["role"], "|", t["name"], "| processing:", t.get("processing"))

# 2) 资产清单与关键资产
assets = c.request("GET", f"themes/{TID}/assets.json").get("assets", [])
keys = [a["key"] for a in assets]
need = ["layout/theme.liquid", "config/settings_data.json", "config/settings_schema.json",
        "sections/main-product.liquid", "templates/product.json",
        "sections/header.liquid", "sections/footer.liquid",
        "sections/collapsible-content.liquid"]
print("total assets:", len(keys), "| text:", sum(1 for a in assets if a.get("content_type") != "image"))
print("key assets present:", {k.split("/")[-1]: (k in keys) for k in need})


def get(key: str) -> str:
    return c.request("GET", f"themes/{TID}/assets.json",
                     params={"asset[key]": key})["asset"].get("value", "") or ""


# 3) theme.liquid 现状（是否已有注入痕迹）
tl = get("layout/theme.liquid")
print("theme.liquid bytes:", len(tl), "| bomi-schema mark:", "bomi-schema-v1" in tl)

# 4) 自带结构化数据：main-product 与 collapsible-content
mp = get("sections/main-product.liquid")
print("main-product.liquid bytes:", len(mp), "| ld+json:", mp.count("application/ld+json"))
if "application/ld+json" in mp:
    i = mp.find("application/ld+json")
    print("  ld context:", mp[max(0, i - 220):i + 60].replace("\n", " ")[:300])
for k in ("sections/collapsible-content.liquid", "snippets/faq.liquid"):
    if k in keys:
        s = get(k)
        print(f"{k}: ld+json={s.count('application/ld+json')} FAQPage={s.count('FAQPage')}")

# 5) settings_data.json 现状
try:
    sd = json.loads(get("config/settings_data.json"))
    cur = sd.get("current", {})
    print("settings_data preset:", sd.get("preset_id"), "| current keys:", len(cur))
    for k in ("favicon", "logo", "type_header_font", "type_body_font",
              "color_scheme_group", "cart_type", "sections_header"):
        if k in cur:
            print("  ", k, "=", str(cur[k])[:110].replace("\n", " "))
    cs = cur.get("color_scheme_group")
    if isinstance(cs, dict):
        print("   color schemes:", {sk: list(sv.get("settings", {}).keys())[:4]
                                     for sk, sv in list(cs.items())[:2]})
except Exception as e:
    print("settings_data parse ERR:", str(e)[:120])

# 6) 预览基线：新主题预览主页
r = subprocess.run(["curl", "-sk", "-o", "/dev/null", "-w", "%{http_code}",
                    f"https://www.estrybattery.com/?preview_theme_id={TID}"],
                   capture_output=True, text=True, timeout=60)
print("preview home status:", r.stdout)

# 7) draft 产品在新主题预览下渲染（GraphQL previewUrl + preview_theme_id 叠加）
q = {"query": "{ products(first: 1, query: \"status:draft\") "
              "{ nodes { title onlinePreviewUrl } } }"}
g = c.request("POST", "graphql.json", json_body=q)
try:
    node = g["data"]["products"]["nodes"][0]
    url = node["onlinePreviewUrl"]
    print("draft:", node["title"][:40], "| previewUrl ok:", bool(url))
    sep = "&" if "?" in url else "?"
    full = f"{url}{sep}preview_theme_id={TID}"
    r2 = subprocess.run(["curl", "-skL", "-o", "/tmp/dawn_prod.html", "-w", "%{http_code}", full],
                        capture_output=True, text=True, timeout=60)
    html = open("/tmp/dawn_prod.html", encoding="utf-8", errors="ignore").read()
    print("preview product status:", r2.stdout,
          "| body-table:", "Specification</h3>" in html or "spec" in html.lower()[:200000],
          "| FAQ-details:", "<details" in html,
          "| ld+json blocks:", html.count("application/ld+json"))
except Exception as e:
    print("draft preview ERR:", str(e)[:150], "| raw:", str(g)[:200])
