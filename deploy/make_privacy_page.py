# -*- coding: utf-8 -*-
"""创建 Google 验证用隐私政策页 /pages/privacy-policy。
含: 新域名、数据收集/使用、Google Ads API 披露(含有限使用与 AI NCII 否认)、
GDPR/CCPA、联系方式。幂等: 已存在则更新。
"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

shop = cl._client.get("shop.json", auth=cl._auth).json()["shop"]
email = shop.get("customer_email") or shop.get("email") or "support@estrybattery.com"
print("店铺联系方式:", email)

BODY = f"""
<p>Last updated: November 5, 2026</p>
<p>This Privacy Policy describes how Estry ("we", "us", or "our") collects, uses, and discloses personal information when you visit or make a purchase from <strong>www.estrybattery.com</strong> (the "Site"). Estry is a professional battery supplier based in Hong Kong that sells replacement batteries and related products to customers worldwide.</p>

<h2>1. Personal Information We Collect</h2>
<p>When you visit the Site, we automatically collect certain information about your device, including your web browser, IP address, time zone, and some of the cookies installed on your device. We additionally collect information about you when you interact with the Site, such as pages viewed, products browsed, referring website, and actions taken ("Device Information").</p>
<p>When you create an account or purchase through the Site, we collect information that can identify you, including your name, email address, postal address, phone number, order history, and payment details processed securely by our payment providers ("Order Information"). Device Information is collected using cookies and similar tracking technologies (see Section 6).</p>

<h2>2. How We Use Your Information</h2>
<ul>
<li>Fulfilling and processing your orders, including payment verification, shipping, returns, and customer support;</li>
<li>Improving and optimizing the Site, products, and services, including analytics of browsing and purchasing behavior;</li>
<li>Communicating with you about orders, promotions, and updates, where you have opted in;</li>
<li>Detecting and preventing fraud and abuse of the Site;</li>
<li>Advertising and marketing, including running and managing our own advertising campaigns on Google and other platforms;</li>
<li>Complying with legal obligations.</li>
</ul>

<h2>3. Google API Services — Data Use Disclosure</h2>
<p>We use the <strong>Google Ads API</strong> and related Google services to manage our own advertising campaigns for the Site. Specifically:</p>
<ul>
<li><strong>Which Google APIs we use:</strong> Google Ads API (campaign management, performance reporting, and audience management for our own campaigns).</li>
<li><strong>What user data is used:</strong> limited, coarse advertising data such as hashed contact details provided with consent for remarketing audiences, conversion events (e.g., completed orders), and aggregated campaign statistics. We do not use Google APIs to collect sensitive personal categories.</li>
<li><strong>How the data is used:</strong> solely to create, manage, and measure our own advertising campaigns and to improve our services. Data is not sold, and it is not used to contact you directly outside of orders and opt-in marketing.</li>
<li><strong>Google API Services User Data Policy:</strong> our use of Google APIs complies with the Google API Services User Data Policy, including the Limited Use requirements.</li>
<li><strong>AI NCII:</strong> We do <strong>not</strong> use Google APIs (or any other technology) to generate, process, or distribute AI-generated non-consensual intimate images (AI NCII). Our Site and applications are used exclusively for the lawful operation of our battery e-commerce business.</li>
</ul>

<h2>4. Sharing Your Information</h2>
<p>We share your personal information only as necessary to operate our business: with payment processors (e.g., credit card processors, PayPal), shipping carriers, and service providers that assist us with the Site (e.g., hosting, analytics, email delivery). Each party processes data under its own privacy policy. We may also disclose information to comply with law, regulation, or legal process, or to protect the rights, property, or safety of our customers and others.</p>

<h2>5. Data Retention and Security</h2>
<p>We retain personal information only as long as necessary for the purposes described in this policy and to comply with our legal obligations. We use reasonable administrative, technical, and physical safeguards to protect your personal information; however, no method of transmission over the Internet is 100% secure.</p>

<h2>6. Cookies and Tracking Technologies</h2>
<p>We use cookies to maintain your session, remember shopping cart contents, and understand how the Site is used (e.g., Google Analytics, Shopify analytics). You can instruct your browser to refuse cookies; some parts of the Site may then not function. Advertising cookies help us show relevant ads on Google and other networks, and you may opt out of personalized advertising via Google Ads Settings.</p>

<h2>7. Your Rights</h2>
<p>Depending on your location (e.g., EEA/UK under GDPR, California under CCPA/CPRA), you may have rights to access, correct, delete, or export your personal information, to restrict or object to certain processing, and to lodge a complaint with a supervisory authority. California residents have the right to opt out of "sale/sharing" of personal information and to non-discrimination. To exercise any right, contact us at {email}.</p>

<h2>8. Children's Privacy</h2>
<p>The Site is not intended for children under 13 (or under 16 in the EEA), and we do not knowingly collect personal information from children.</p>

<h2>9. Changes and Contact</h2>
<p>We may update this policy from time to time; the "Last updated" date above reflects the latest revision. Questions? Contact us at <a href="mailto:{email}">{email}</a>.</p>
"""

r = cl._client.get("pages.json", params={"limit": 250}, auth=cl._auth)
r.raise_for_status()
pages = r.json()["pages"]
ex = next((p for p in pages if p["handle"] == "privacy-policy"), None)
if ex:
    r = cl._client.put(f"pages/{ex['id']}.json", auth=cl._auth,
                       json={"page": {"id": ex["id"], "body_html": BODY,
                                      "published": True}})
    r.raise_for_status()
    print("已更新 page id", ex["id"])
else:
    r = cl._client.post("pages.json", auth=cl._auth, json={"page": {
        "title": "Privacy Policy", "handle": "privacy-policy",
        "body_html": BODY, "published": True}})
    r.raise_for_status()
    print("已创建 page id", r.json()["page"]["id"])
print("URL: https://www.estrybattery.com/pages/privacy-policy")
