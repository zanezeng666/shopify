"""向 Dawn theme.liquid 注入 FAQPage JSON-LD（仅产品页 guard，幂等可回滚）。

Dawn v16 原生已输出 Product JSON-LD（{{ product | structured_data }}），
本脚本只补 FAQPage（FAQ 内容在产品 body 的 details 里，主题不感知）。
用法：
  sudo -u jason .venv/bin/python inject_faq_dawn.py             # 注入
  sudo -u jason .venv/bin/python inject_faq_dawn.py --rollback  # 备份回滚
"""
import glob
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

TID = 190031036660
KEY = "layout/theme.liquid"
MARK = "<!-- estry-faq-schema-v1 -->"
c = ShopifyRest(StoreService().get_client(1)).client

BLOCK = """
<!-- estry-faq-schema-v1 -->
{% comment %} Estry FAQPage structured data (product pages only) {% endcomment %}
{% if template contains 'product' %}
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
<!-- /estry-faq-schema-v1 -->
"""


def get_val() -> str:
    return c.request("GET", f"themes/{TID}/assets.json",
                     params={"asset[key]": KEY})["asset"]["value"]


if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
    baks = sorted(glob.glob("/tmp/theme.dawn.bak-*"))
    if not baks:
        sys.exit("no backup found")
    with open(baks[-1], encoding="utf-8") as f:
        old = f.read()
    c.request("PUT", f"themes/{TID}/assets.json",
              json_body={"asset": {"key": KEY, "value": old}})
    print("rolled back from:", baks[-1])
    sys.exit(0)

cur = get_val()
print("current bytes:", len(cur))
if MARK in cur:
    sys.exit("already injected, skip (idempotent)")
if "</head>" not in cur:
    sys.exit("ERROR: no </head> in Dawn theme.liquid, abort")

bak = f"/tmp/theme.dawn.bak-{time.strftime('%Y%m%d-%H%M%S')}"
with open(bak, "w", encoding="utf-8") as f:
    f.write(cur)
print("backup:", bak)

c.request("PUT", f"themes/{TID}/assets.json",
          json_body={"asset": {"key": KEY,
                               "value": cur.replace("</head>", BLOCK + "\n</head>", 1)}})
time.sleep(6)  # 资产读传播延迟

chk = get_val()
print("injected:", MARK in chk,
      "| ld+json in theme.liquid:", chk.count("application/ld+json"),
      "| bytes:", len(cur), "->", len(chk))
