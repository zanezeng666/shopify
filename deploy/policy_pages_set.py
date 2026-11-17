# -*- coding: utf-8 -*-
"""政策页落地：Shipping/Refund 政策充实 + Warranty 页创建 + footer 补链接。
幂等可重跑；先打印现状再更新。"""
import json
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

TID = "190031036660"
c = ShopifyRest(StoreService().get_client(1)).client

SHIPPING_BODY = """<h2>Shipping Policy</h2>
<p>At Estry, we ship replacement batteries for medical devices from our US warehouse directly to your door.</p>
<h3>Processing Time</h3>
<ul>
<li>Orders placed before 2:00 PM (EST) on business days are processed the same day.</li>
<li>Standard processing time is 1&ndash;2 business days after payment confirmation.</li>
</ul>
<h3>Shipping Methods &amp; Delivery Times (United States)</h3>
<ul>
<li><strong>Free Standard Shipping</strong> &mdash; 3&ndash;6 business days &mdash; <strong>FREE on all US orders</strong>.</li>
<li>Tracking numbers are emailed automatically once your order ships.</li>
</ul>
<h3>International Shipping</h3>
<p>We currently ship to Canada, Mexico, United Kingdom, and South Africa. Available methods and rates are calculated at checkout based on destination and order weight.</p>
<h3>Shipping Safety (Batteries)</h3>
<p>All lithium batteries are packed in UN 38.3 certified packaging and shipped in compliance with applicable transport regulations.</p>
<h3>Questions</h3>
<p>Contact us at <a href="mailto:support@estrybattery.com">support@estrybattery.com</a> with your order number for any shipping inquiry.</p>"""

REFUND_BODY = """<h2>Refund &amp; Return Policy</h2>
<p>We want you to be completely satisfied with your Estry replacement battery. If something is not right, we will make it right.</p>
<h3>30-Day Return Window</h3>
<ul>
<li>You may return any product within <strong>30 days of delivery</strong> for a refund or replacement.</li>
<li>To qualify, the battery must be in resalable condition with original packaging where practical.</li>
</ul>
<h3>Defective or Incorrect Items</h3>
<ul>
<li>If your battery arrives defective, damaged, or is the wrong model, we cover all costs: we send a prepaid return label and ship a free replacement (or issue a full refund, your choice).</li>
<li>Report the issue within 7 days of delivery with your order number and a short description (photos help).</li>
</ul>
<h3>Refund Process</h3>
<ul>
<li>Once your return is received and inspected, refunds are issued to the original payment method within 3&ndash;5 business days.</li>
<li>Original shipping charges are refunded when the return is due to our error.</li>
</ul>
<h3>Battery Safety Note</h3>
<p>Do not ship back swollen, leaking, or physically damaged batteries &mdash; contact us first for safe disposal guidance and an immediate replacement.</p>
<h3>How to Start a Return</h3>
<p>Email <a href="mailto:support@estrybattery.com">support@estrybattery.com</a> with your order number and the issue. We reply within 1 business day.</p>"""

WARRANTY_BODY = """<h2>Estry 12-Month Warranty</h2>
<p>Every battery purchased from Estrybattery.com is covered by a <strong>12-month limited warranty</strong> against manufacturing defects.</p>
<h3>What Is Covered</h3>
<ul>
<li>Manufacturing defects in materials and workmanship.</li>
<li>Battery failure to hold rated capacity under normal use within 12 months of purchase.</li>
<li>Premature battery death (significantly below rated cycle life) under normal operating conditions.</li>
</ul>
<h3>What Is Not Covered</h3>
<ul>
<li>Physical damage, drops, or crushing after delivery.</li>
<li>Damage from improper charging equipment or unauthorized repair.</li>
<li>Normal wear beyond 12 months from purchase date.</li>
</ul>
<h3>How to Claim</h3>
<ol>
<li>Email <a href="mailto:support@estrybattery.com">support@estrybattery.com</a> with your order number, device model, and a description of the issue.</li>
<li>We reply within 1 business day with troubleshooting steps if needed.</li>
<li>If the battery is confirmed defective, we ship a free replacement right away &mdash; no need to wait for the return to arrive.</li>
</ol>
<h3>Quality You Can Trust</h3>
<p>Our batteries are manufactured in ISO-certified facilities, tested to UN 38.3 transport standards, and built with grade-A cells. Certificates are available on our <a href="/pages/certificates">Certificates page</a>.</p>"""

# --- 1) 现状：列出政策 ---
pols = c.request("GET", "policies.json").get("policies", [])
print("现有政策:", [(p["handle"], p["title"], len(p.get("body") or "")) for p in pols])

# --- 2) 更新 shipping/refund 政策（shopPolicyUpdate 按枚举 type）---
for handle, ptype, body in (
        ("shipping-policy", "SHIPPING_POLICY", SHIPPING_BODY),
        ("refund-policy", "REFUND_POLICY", REFUND_BODY)):
    try:
        c.graphql(
            "mutation($p: ShopPolicyInput!) { shopPolicyUpdate("
            "shopPolicy: $p) { __typename } }",
            {"p": {"type": ptype, "body": body}})
        print(f"政策 {handle}: OK")
    except Exception as e:  # noqa: BLE001
        print(f"政策 {handle}: FAIL {str(e)[:150]}")

# --- 3) Warranty 页（查重建）---
pages = c.request("GET", "pages.json",
                  params={"limit": 250, "handle": "warranty"}).get("pages", [])
if pages:
    pid = pages[0]["id"]
    try:
        c.request("PUT", f"pages/{pid}.json", json_body={"page": {
            "title": "Warranty - 12-Month Battery Warranty",
            "body_html": WARRANTY_BODY, "published": True}})
        print("warranty 页更新: OK")
    except Exception as e:  # noqa: BLE001
        print(f"warranty 页更新: FAIL {str(e)[:150]}")
else:
    try:
        c.request("POST", "pages.json", json_body={"page": {
            "title": "Warranty - 12-Month Battery Warranty",
            "handle": "warranty",
            "body_html": WARRANTY_BODY, "published": True}})
        print("warranty 页创建: OK")
    except Exception as e:  # noqa: BLE001
        print(f"warranty 页创建: FAIL {str(e)[:150]}")

# --- 4) footer.liquid 补 Warranty 链接（FAQ 行后插 li）---
a = c.request("GET", f"themes/{TID}/assets.json",
              params={"asset[key]": "sections/footer.liquid"})
val = a.get("asset", {}).get("value", "")
if not val:
    print("!! footer.liquid 读取失败")
elif "/pages/warranty" in val:
    print("footer 已含 warranty 链接，跳过")
else:
    anchor = ('<li><small class="copyright__content">'
              '<a href="/pages/faq">FAQ</a></small></li>')
    if anchor not in val:
        print("!! 未找到 FAQ 锚点行")
    else:
        ins = anchor + ('\n        <li><small class="copyright__content">'
                        '<a href="/pages/warranty">Warranty</a></small></li>')
        val2 = val.replace(anchor, ins, 1)
        try:
            c.request("PUT", f"themes/{TID}/assets.json", json_body={
                "asset": {"key": "sections/footer.liquid", "value": val2}})
            print("footer 链接插入: OK")
        except Exception as e:  # noqa: BLE001
            print(f"footer 链接插入: FAIL {str(e)[:150]}")

# --- 5) 回读断言 ---
pol2 = c.request("GET", "policies.json").get("policies", [])
for p in pol2:
    if p["handle"] in ("shipping-policy", "refund-policy"):
        print(f"断言 {p['handle']}: body={len(p.get('body') or '')} chars "
              f"{'PASS' if len(p.get('body') or '') > 1000 else 'FAIL'}")
pg = c.request("GET", "pages.json",
               params={"limit": 10, "handle": "warranty"}).get("pages", [])
print("断言 warranty 页:", "PASS" if pg else "FAIL")
