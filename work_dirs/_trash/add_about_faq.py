# -*- coding: utf-8 -*-
"""About Us + FAQ 页创建（幂等）+ footer 菜单追加链接。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

rest = ShopifyRest(StoreService().get_client(1)).client

CSS = """<style>
.ea-wrap{max-width:80rem;margin:0 auto;padding:0 1.6rem;}
.ea-hero{background:#01448D;color:#fff;border-radius:14px;padding:34px 30px;margin:22px 0;}
.ea-hero h1{margin:0 0 10px;font-size:2.6rem;color:#fff;}
.ea-hero p{margin:0;font-size:1.6rem;color:#cfe0f2;max-width:70rem;}
.ea-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin:20px 0;}
.ea-card{border:1px solid #e3e9f0;border-radius:12px;padding:20px;}
.ea-card b{color:#01448D;display:block;margin-bottom:6px;font-size:1.7rem;}
.ea-card p{margin:0;color:#4a5568;font-size:1.45rem;line-height:1.55;}
.ea-nums{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:20px 0;}
.ea-num{background:#f0f6fc;border-radius:12px;padding:18px;text-align:center;}
.ea-num b{display:block;font-size:2.4rem;color:#01448D;}
.ea-num span{color:#4a5568;font-size:1.35rem;}
.ea-cta{background:#16233a;border-radius:12px;padding:24px;display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;margin:20px 0 30px;}
.ea-cta p{margin:0;color:#dbe5f0;font-size:1.6rem;}
.ea-cta a{background:#84C227;color:#fff;border-radius:9px;padding:12px 24px;font-weight:700;text-decoration:none;font-size:1.5rem;}
.ef-faq{max-width:80rem;margin:0 auto;padding:0 1.6rem 30px;}
.ef-faq h2{color:#01448D;}
details{border:1px solid #e3e9f0;border-radius:10px;margin:10px 0;padding:0 18px;background:#fff;}
details summary{cursor:pointer;font-weight:700;padding:15px 0;font-size:1.6rem;color:#1b2a41;list-style:none;display:flex;justify-content:space-between;align-items:center;}
details summary::after{content:'+';font-size:2rem;color:#84C227;}
details[open] summary::after{content:'\2212';}
details .a{padding:0 0 16px;color:#4a5568;font-size:1.5rem;line-height:1.6;}
</style>"""

ABOUT_BODY = CSS + """
<div class="ea-wrap">
<div class="ea-hero">
<h1>Replacement batteries for professional &amp; medical equipment</h1>
<p>Estry supplies drop-in replacement battery packs for infusion pumps, defibrillators, patient monitors, power tools, scanners, two-way radios and other professional devices &mdash; 8,700+ models cross-referenced against OEM part numbers, so you order by what the label says and we match the rest.</p>
</div>
<div class="ea-nums">
<div class="ea-num"><b>8,700+</b><span>replacement models</span></div>
<div class="ea-num"><b>24h</b><span>quote turnaround</span></div>
<div class="ea-num"><b>48h</b><span>sample dispatch</span></div>
<div class="ea-num"><b>3</b><span>warehouses CN / HK / US</span></div>
</div>
<div class="ea-grid">
<div class="ea-card"><b>Cross-reference matching</b><p>Send models, OEM part numbers, device names &mdash; even photos of the label. Our engineers confirm compatibility, connector and fit before quoting.</p></div>
<div class="ea-card"><b>Compliance documents</b><p>UN 38.3 test summaries and MSDS/SDS available for every shipment. Documents are issued with your order &mdash; no extra requests needed.</p></div>
<div class="ea-card"><b>Volume pricing</b><p>Automatic tiered discounts at checkout &mdash; 10+ pcs &minus;5%, 100+ pcs &minus;10%, mix &amp; match any models. Deeper pricing for recurring B2B volumes via quote.</p></div>
<div class="ea-card"><b>Fast logistics</b><p>Free shipping to the United States on every order. Samples dispatch in 48 hours; bulk orders ship with PI and a full compliance pack.</p></div>
</div>
<div class="ea-cta">
<p>Need a model you can't find? Our engineers cross-reference it for you &mdash; reply within 24 hours.</p>
<a href="/pages/wholesale">Request a Quote</a>
</div>
</div>
"""

FAQS = [
    ("How do I find the right battery for my device?",
     "Use the <a href='/pages/battery-search'>Battery Finder</a> to search by battery model, device brand, OEM part number or device model. If nothing matches, send the label photo or part list through the <a href='/pages/wholesale'>quote form</a> — we cross-reference for you within 24 hours."),
    ("What is the minimum order quantity?",
     "There is no minimum for stock orders — you can buy a single unit at the online price. For custom packs or unlisted models, MOQ depends on the pack; the quote will state it clearly."),
    ("Do you offer volume discounts?",
     "Yes — automatic at checkout, mix &amp; match any models: 10+ pcs −5%, 20+ pcs −6%, 50+ pcs −8%, 100+ pcs −10%. For recurring or larger volumes, request a quote for deeper pricing."),
    ("How fast is shipping? Is it free?",
     "Shipping to the United States is free on every order. Samples dispatch within 48 hours; bulk lead time is confirmed on your quote. Other destinations and terms (FOB/EXW/DAP) are quoted per order."),
    ("What compliance documents do you provide?",
     "UN 38.3 test summary and MSDS/SDS are available for every battery model and issued with your order and shipment."),
    ("Can I get samples before a bulk order?",
     "Yes. Sample orders ship in 48 hours at the online single-unit price, and sample cost is deducted from your first bulk order — mention it in the quote form."),
    ("What if a battery is defective?",
     "Defective units are replaced free of charge. Email your order number and photos and we will arrange the replacement with your next shipment or separately."),
    ("Do you support OEM / custom battery packs?",
     "Yes — custom packs, connectors, labels and packaging are quoted per project. Send the specification or a sample through the quote form."),
]

ld = {"@context": "https://schema.org", "@type": "FAQPage",
      "mainEntity": [{"@type": "Question", "name": q,
                      "acceptedAnswer": {"@type": "Answer", "text": a.replace("&amp;", "&")}}
                     for q, a in FAQS]}

FAQ_BODY = CSS + '<div class="ef-faq"><h1>Frequently Asked Questions</h1>' + "".join(
    f"<details><summary>{q}</summary><div class='a'>{a}</div></details>" for q, a in FAQS
) + f"<script type='application/ld+json'>{json.dumps(ld, ensure_ascii=False)}</script></div>"

PAGES = [
    {"title": "About Estry — Professional Replacement Batteries", "handle": "about",
     "body_html": ABOUT_BODY, "template_suffix": ""},
    {"title": "FAQ — Orders, Shipping, Compliance | Estry", "handle": "faq",
     "body_html": FAQ_BODY, "template_suffix": ""},
]

for p in PAGES:
    ex = rest.request("GET", "pages.json",
                      params={"handle": p["handle"], "limit": 1}).get("pages", [])
    if ex:
        rest.request("PUT", f"pages/{ex[0]['id']}.json", json_body={"page": {"id": ex[0]["id"], **p}})
        print("updated", p["handle"])
    else:
        rest.request("POST", "pages.json", json_body={"page": {**p, "published": True}})
        print("created", p["handle"])

# footer 菜单追加 About/FAQ（幂等）
import time
time.sleep(2)
try:
    menu = None
    for hm in rest.request("GET", "menus.json").get("menus", []):
        if hm.get("handle") == "footer":
            menu = hm
            break
    if not menu:
        print("no footer menu found")
    else:
        items = rest.request("GET", f"menus/{menu['id']}.json")["menu"].get("items", [])
        titles = {i["title"] for i in items}
        add = []
        for t, u in [("About Us", "/pages/about"), ("FAQ", "/pages/faq")]:
            if t not in titles:
                add.append({"type": "link", "title": t, "url": u})
        if add:
            new_items = [{"type": i.get("type", "link"), "title": i["title"],
                          "url": i.get("url", "")} for i in items] + add
            rest.request("PUT", f"menus/{menu['id']}.json", json_body={"menu": {"id": menu["id"], "items": new_items}})
            print("footer menu +", [a["title"] for a in add])
        else:
            print("footer menu already has links")
except Exception as e:
    print("menu err:", str(e)[:200])
