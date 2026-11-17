"""诊断 Estry 店铺本地化：shop 货币/地址国 + markets 列表 + 首页默认 country selector。"""
import json
import re
import subprocess
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

client = ShopifyRest(StoreService().get_client(1)).client

# 1) shop 基本信息
q = """
{
  shop {
    name
    currencyCode
    billingAddress { country }
  }
}
"""
r = client.graphql(q)
print("== shop ==")
print(json.dumps(r, ensure_ascii=False, indent=1, default=str))

# 2) markets（若 API 版本支持）
q2 = """
{
  markets(first: 30) {
    nodes {
      id
      name
      handle
      enabled
      primary
    }
  }
}
"""
try:
    r2 = client.graphql(q2)
    print("== markets ==")
    print(json.dumps(r2, ensure_ascii=False, indent=1, default=str))
except Exception as e:
    print("markets query failed:", e)

# 3) 首页默认本地化（无 cookie 抓取）
html = subprocess.run(
    ["curl", "-s", "-A", "Mozilla/5.0", "https://www.estrybattery.com/"],
    capture_output=True, text=True,
).stdout
# localization form 里选中的 option / input value
m = re.search(r'name="country_code"[^>]*value="([A-Z]{2})"', html)
print("== storefront ==")
print("country input value:", m.group(1) if m else "(not found)")
for pat in [r"localization[^\"]*current[^\"]*\">([^<]{2,40})<", r"data-localization[^>]*>.*?</", r"(Hong Kong SAR|United States)[^<]{0,20}\(USD ?\$?\)"]:
    mm = re.findall(pat, html)
    if mm:
        print(pat[:40], "->", mm[:5])
# published locales
ml = re.findall(r"hreflang=\"([a-z]{2}(?:-[A-Za-z]{2})?)\"", html)
print("hreflang:", sorted(set(ml)))
