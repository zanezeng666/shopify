"""主题 theme.liquid 注入 Product/Offer/FAQPage JSON-LD（幂等，可回滚，可升级）。

背景：Shopify 会剥 body_html 里的 script，结构化数据必须由主题输出；
22 个产品 draft 未发布，本改动不影响任何前台页面。

用法（服务器上执行）:
  sudo -u jason .venv/bin/python inject_schema.py             # 注入（已注入则跳过）
  sudo -u jason .venv/bin/python inject_schema.py --update    # 用当前 BLOCK 整块替换旧注入块
  sudo -u jason .venv/bin/python inject_schema.py --rollback  # 用最新备份回滚

注意：Shopify 主题资产 PUT 后 GET 有秒级传播延迟，本脚本 PUT 后延迟复查。
v1.1：image 行 image_url → img_url（老店铺资产上 image_url 报 invalid url input）。
"""
import glob
import re
import subprocess
import sys
import time
from datetime import datetime

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

THEME_ID = 136764817652  # Buy on Amazon Simple (role=main)
ASSET_KEY = "layout/theme.liquid"
MARK = "bomi-schema-v1"
BAK_GLOB = "/tmp/theme.liquid.bak-*"
HOME = "https://www.bornmieo.com/"

# 全部用 Liquid 对象动态渲染（零维护，新品自动生效）；
# 字符串一律过 | json 过滤器保证合法 JSON 转义。
BLOCK = """<!-- bomi-schema-v1 -->
{% if template contains 'product' %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": {{ product.title | json }},
  "brand": {"@type": "Brand", "name": {{ product.vendor | json }}},
  "sku": {{ product.selected_or_first_available_variant.sku | json }},
  "mpn": {{ product.selected_or_first_available_variant.sku | json }},
  "description": {{ product.description | strip_html | truncate: 300 | json }},
  "image": {{ product.featured_image | img_url: "1200x1200" | prepend: "https:" | json }},
  "offers": {
    "@type": "Offer",
    "price": {{ product.selected_or_first_available_variant.price | divided_by: 100.0 | json }},
    "priceCurrency": {{ cart.currency.iso_code | json }},
    "availability": "https://schema.org/{% if product.selected_or_first_available_variant.available %}InStock{% else %}OutOfStock{% endif %}",
    "itemCondition": "https://schema.org/NewCondition",
    "url": "https://{{ shop.domain }}{{ product.url }}"
  }
}
</script>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {"@type": "Question",
     "name": "How do I confirm this battery fits my device?",
     "acceptedAnswer": {"@type": "Answer", "text": "Match your device against the Compatible Model list, or compare the part number printed on your original battery. Still unsure? Email us with your battery details or photos and we will help you confirm."}},
    {"@type": "Question",
     "name": "What is the warranty policy?",
     "acceptedAnswer": {"@type": "Answer", "text": "This battery is covered by a 12-month warranty against manufacturing defects, plus 30-day easy returns for peace of mind."}},
    {"@type": "Question",
     "name": "How fast will my order arrive?",
     "acceptedAnswer": {"@type": "Answer", "text": "In-stock orders ship from our US warehouse within 48 hours on business days."}}
  ]
}
</script>
{% endif %}
<!-- /bomi-schema-v1 -->
"""

c = ShopifyRest(StoreService().get_client(1)).client


def get_value() -> str:
    a = c.request("GET", f"themes/{THEME_ID}/assets.json",
                  params={"asset[key]": ASSET_KEY})
    return a["asset"]["value"]


def put_value(v: str) -> None:
    c.request("PUT", f"themes/{THEME_ID}/assets.json",
              json_body={"asset": {"key": ASSET_KEY, "value": v}})


def homepage_status() -> str:
    r = subprocess.run(["curl", "-sk", "-o", "/dev/null", "-w", "%{http_code}",
                        HOME], capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
    baks = sorted(glob.glob(BAK_GLOB))
    if not baks:
        sys.exit("no backup found")
    bak = baks[-1]
    with open(bak, encoding="utf-8") as f:
        put_value(f.read())
    cur = get_value()
    print("rolled back from:", bak)
    print("mark absent:", MARK not in cur, "| bytes:", len(cur))
    print("homepage:", homepage_status())
    sys.exit(0)

cur = get_value()
print("current bytes:", len(cur))

if len(sys.argv) > 1 and sys.argv[1] == "--update":
    pat = re.compile(r"<!-- bomi-schema-v1 -->.*?<!-- /bomi-schema-v1 -->\n?", re.S)
    if not pat.search(cur):
        sys.exit("ERROR: old block not found, nothing to update")
    new = pat.sub(BLOCK + "\n", cur, count=1)
    put_value(new)
    time.sleep(6)  # 资产读传播延迟
    chk = get_value()
    print("updated:", chk.count("application/ld+json") == 2,
          "| img_url used:", 'img_url: "1200x1200"' in chk,
          "| bytes:", len(cur), "->", len(chk))
    print("homepage:", homepage_status())
    sys.exit(0)

if MARK in cur:
    sys.exit("already injected, skip (idempotent)")
if "</head>" not in cur:
    sys.exit("ERROR: no </head> in theme.liquid, abort")

bak = f"/tmp/theme.liquid.bak-{datetime.now():%Y%m%d-%H%M%S}"
with open(bak, "w", encoding="utf-8") as f:
    f.write(cur)
print("backup:", bak)

new = cur.replace("</head>", BLOCK + "\n</head>", 1)
put_value(new)
time.sleep(6)  # 资产读传播延迟

chk = get_value()
print("injected:", MARK in chk, "| bytes:", len(cur), "->", len(chk))
print("product-guard count:", chk.count("{% if template contains 'product' %}"))
print("ld+json blocks:", chk.count("application/ld+json"))
print("homepage:", homepage_status())
