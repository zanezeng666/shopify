# -*- coding: utf-8 -*-
"""Estry 询盘页 + 证书页 (B2B 四件套之三/四).

  1. 上传 sections/estry-wholesale.liquid (原生 contact form 批量询价+信任栏)
  2. 上传 sections/estry-certificates.liquid (证书卡片+索取流程)
  3. 上传 templates/page.wholesale.json / page.certificates.json
  4. 创建 /pages/wholesale 与 /pages/certificates, 线上断言
用法:
  sudo -u jason env HOME=/home/jason .venv/bin/python add_inquiry_cert.py
"""
import json
import sys
import time
import urllib.request

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

TID = 190031036660
c = ShopifyRest(StoreService().get_client(1)).client

WHOLESALE = r"""{% comment %} estry-wholesale-v2: B2B inquiry + volume tiers {% endcomment %}
<section class="wsi">
  <div class="wsi-hero">
    <div class="page-width">
      <p class="wsi-hero__k">{{ section.settings.kicker | escape }}</p>
      <h1 class="wsi-hero__t">{{ section.settings.heading | escape }}</h1>
      <p class="wsi-hero__s">{{ section.settings.sub | escape }}</p>
    </div>
  </div>

  <div class="wsi-body page-width">
    <div class="wsi-formcard">
      {%- if form.posted_successfully? -%}
      <div class="wsi-ok">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="m8 12 3 3 5-6"/></svg>
        <h2>Inquiry received</h2>
        <p>Thank you &mdash; our sales engineer will reply with pricing and documents <b>within 24 hours</b> (Mon&ndash;Sat).</p>
        <a class="wsi-ok__btn" href="/pages/battery-search">Back to Battery Finder</a>
      </div>
      {%- else -%}
      <div class="wsi-tier">
        <span class="wsi-tier__t">Volume discounts</span>
        <span class="wsi-tier__c">10+ <b>&minus;5%</b></span>
        <span class="wsi-tier__c">20+ <b>&minus;6%</b></span>
        <span class="wsi-tier__c">50+ <b>&minus;8%</b></span>
        <span class="wsi-tier__c">100+ <b>&minus;10%</b></span>
      </div>
      <p class="wsi-tier__n">Automatic at checkout (cart total, mix &amp; match any models) &mdash; or ask us to include tier pricing in your quote.</p>
      {% form 'contact', class: 'wsi-form' %}
        {%- if form.errors -%}
        <div class="wsi-err">{{ form.errors | default_errors }}</div>
        {%- endif -%}
        <div class="wsi-frow wsi-frow--2">
          <div class="wsi-f"><label for="wsi-co">Company *</label><input id="wsi-co" type="text" name="contact[Company]" required placeholder="Company name"></div>
          <div class="wsi-f"><label for="wsi-nm">Contact name *</label><input id="wsi-nm" type="text" name="contact[name]" required placeholder="Your name"></div>
        </div>
        <div class="wsi-frow wsi-frow--2">
          <div class="wsi-f"><label for="wsi-em">Business email *</label><input id="wsi-em" type="email" name="contact[email]" required placeholder="name@company.com"></div>
          <div class="wsi-f"><label for="wsi-ct">Country</label><input id="wsi-ct" type="text" name="contact[Country]" placeholder="e.g. Germany"></div>
        </div>
        <div class="wsi-f"><label for="wsi-md">Battery models / OEM part numbers *</label>
          <textarea id="wsi-md" name="contact[Models]" rows="4" required placeholder="One model per line, e.g.&#10;CS-ZBR138BX &times; 200&#10;Welch Allyn 72300 &times; 50&#10;P1098850-001 &times; 100"></textarea>
          <p class="wsi-hint">Mix battery models, OEM part numbers or device models &mdash; we cross-reference for you.</p>
        </div>
        <div class="wsi-frow wsi-frow--2">
          <div class="wsi-f"><label for="wsi-qt">Est. quantity (total)</label>
            <select id="wsi-qt" name="contact[Quantity]">
              <option value="">Select range</option><option>10 - 50 pcs</option><option>50 - 200 pcs</option><option>200 - 500 pcs</option><option>500 - 1,000 pcs</option><option>1,000 - 5,000 pcs</option><option>5,000+ pcs</option>
            </select></div>
          <div class="wsi-f"><label for="wsi-pr">Target unit price (optional)</label><input id="wsi-pr" type="text" name="contact[Target Price]" placeholder="e.g. $8.50"></div>
        </div>
        <div class="wsi-f"><label>I need</label>
          <div class="wsi-needs">
            <label class="wsi-need"><input type="checkbox" name="contact[Need-Quote]" value="Yes" checked><span>Bulk pricing</span></label>
            <label class="wsi-need"><input type="checkbox" name="contact[Need-SpecSheet]" value="Yes"><span>Spec sheets</span></label>
            <label class="wsi-need"><input type="checkbox" name="contact[Need-Certs]" value="Yes"><span>Certificates (UN38.3/MSDS&hellip;)</span></label>
            <label class="wsi-need"><input type="checkbox" name="contact[Need-Sample]" value="Yes"><span>Samples</span></label>
          </div>
        </div>
        <div class="wsi-f"><label for="wsi-ms">Message</label><textarea id="wsi-ms" name="contact[body]" rows="3" placeholder="Delivery terms, deadlines, packaging requirements&hellip;"></textarea></div>
        <input type="text" name="contact[website]" tabindex="-1" autocomplete="off" class="wsi-hp" aria-hidden="true">
        <button type="submit" class="wsi-send">Send Inquiry <span>&mdash; reply in 24h</span></button>
        <p class="wsi-priv">Your data is used only to answer this inquiry. No newsletter, no resale.</p>
      {% endform %}
      {%- endif -%}
    </div>

    <aside class="wsi-trust">
      <div class="wsi-trust__t">Why source from Estry</div>
      <ul class="wsi-tl">
        <li><b>8,700+ models in stock</b><span>22,000+ OEM cross-references across medical, tool, vacuum &amp; radio batteries</span></li>
        <li><b>OEM-grade manufacturing</b><span>Cells, PCM and assembly meet or exceed original specifications</span></li>
        <li><b>Volume tier pricing</b><span>Transparent quantity breaks from 10 pcs</span></li>
        <li><b>Full compliance docs</b><span>UN 38.3 &amp; MSDS on file for every shipment</span></li>
        <li><b>48h dispatch</b><span>Worldwide DHL/FedEx with battery-compliant packaging</span></li>
      </ul>
      <div class="wsi-trust__t wsi-trust__t--2">How it works</div>
      <ol class="wsi-steps">
        <li><i>1</i><div><b>Submit part list</b><span>Any format &mdash; models, OEM numbers or photos of labels</span></div></li>
        <li><i>2</i><div><b>Quote + datasheets</b><span>Within 24h, with tier pricing and lead time</span></div></li>
        <li><i>3</i><div><b>Sample or bulk ship</b><span>Samples in 48h; bulk with PI &amp; compliance pack</span></div></li>
      </ol>
    </aside>
  </div>
</section>

<style>
  .wsi{--navy:#1B2A41;--green:#00A651;--green-d:#008A43;--line:#D9E2EC;--mut:#5A6B7F;}
  .wsi-hero{background:linear-gradient(135deg,#1B2A41 0%,#243a57 60%,#16233a 100%);padding:40px 0 34px;color:#fff;text-align:center;}
  .wsi-hero__k{margin:0 0 6px;font-size:1.2rem;letter-spacing:.14em;text-transform:uppercase;color:#9fd8b8;font-family:var(--font-heading-family);}
  .wsi-hero__t{margin:0 0 10px;font-size:clamp(2.4rem,4vw,3.4rem);color:#fff;font-family:var(--font-heading-family);font-weight:var(--font-heading-weight);}
  .wsi-hero__s{margin:0 auto;max-width:620px;font-size:1.5rem;color:#aebdd2;}
  .wsi-body{display:grid;grid-template-columns:1.55fr 1fr;gap:24px;padding:30px 0 54px;align-items:start;}
  .wsi-formcard{background:#fff;border:1px solid var(--line);border-radius:14px;padding:28px 30px;box-shadow:0 8px 30px rgba(27,42,65,.07);}
  .wsi-tier{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:6px;}
  .wsi-tier__t{font-size:1.3rem;font-weight:700;color:#1B2A41;margin-right:2px;font-family:var(--font-heading-family);}
  .wsi-tier__c{font-size:1.25rem;color:#1B2A41;background:#EDF7F1;border:1px solid #CBE7D6;border-radius:999px;padding:5px 12px;white-space:nowrap;}
  .wsi-tier__c b{color:#008A43;font-weight:700;}
  .wsi-tier__n{margin:0 0 16px;font-size:1.2rem;color:#5A6B7F;}
  .wsi-form{display:flex;flex-direction:column;gap:16px;}
  .wsi-frow--2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
  .wsi-f label{display:block;font-size:1.22rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--navy);margin-bottom:6px;}
  .wsi-f input[type=text],.wsi-f input[type=email],.wsi-f textarea,.wsi-f select{width:100%;border:1.5px solid var(--line);border-radius:9px;padding:11px 13px;font-size:1.45rem;color:var(--navy);background:#fff;outline:none;transition:border .15s,box-shadow .15s;font-family:inherit;}
  .wsi-f textarea{resize:vertical;}
  .wsi-f input:focus,.wsi-f textarea:focus,.wsi-f select:focus{border-color:var(--green);box-shadow:0 0 0 3px rgba(0,166,81,.16);}
  .wsi-hint{margin:5px 0 0;font-size:1.2rem;color:var(--mut);}
  .wsi-needs{display:grid;grid-template-columns:1fr 1fr;gap:8px;}
  .wsi-need{display:flex;align-items:center;gap:9px;border:1.5px solid var(--line);border-radius:9px;padding:10px 13px;cursor:pointer;font-size:1.35rem;color:#2A3B4F;transition:all .15s;}
  .wsi-need:hover{border-color:var(--green);}
  .wsi-need input{accent-color:var(--green);width:16px;height:16px;}
  .wsi-hp{position:absolute;left:-9999px;height:0;width:0;opacity:0;}
  .wsi-send{margin-top:4px;height:52px;border:none;border-radius:10px;background:var(--green);color:#fff;font-size:1.6rem;font-weight:700;cursor:pointer;transition:background .15s;display:flex;align-items:center;justify-content:center;gap:8px;}
  .wsi-send span{font-weight:400;font-size:1.3rem;color:#cdebda;}
  .wsi-send:hover{background:var(--green-d);}
  .wsi-priv{margin:2px 0 0;font-size:1.15rem;color:var(--mut);text-align:center;}
  .wsi-err{background:#fdecea;border:1px solid #f5c6c0;color:#a4342a;border-radius:9px;padding:10px 14px;font-size:1.35rem;}
  .wsi-ok{text-align:center;padding:40px 10px;}
  .wsi-ok svg{width:64px;height:64px;color:var(--green);margin-bottom:14px;}
  .wsi-ok h2{margin:0 0 8px;font-size:2.6rem;color:var(--navy);font-family:var(--font-heading-family);}
  .wsi-ok p{font-size:1.5rem;color:var(--mut);margin:0 0 22px;}
  .wsi-ok__btn{display:inline-block;background:var(--navy);color:#fff;border-radius:9px;padding:13px 26px;font-size:1.45rem;font-weight:700;text-decoration:none;}
  .wsi-trust{background:#16233a;border-radius:14px;padding:26px 26px 22px;color:#dbe5f0;}
  .wsi-trust__t{font-size:1.4rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#9fd8b8;font-family:var(--font-heading-family);margin-bottom:14px;}
  .wsi-trust__t--2{margin-top:24px;}
  .wsi-tl{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:14px;}
  .wsi-tl li{display:flex;flex-direction:column;gap:2px;border-left:3px solid var(--green);padding-left:12px;}
  .wsi-tl b{font-size:1.4rem;color:#fff;}
  .wsi-tl span{font-size:1.25rem;color:#8fa2ba;line-height:1.45;}
  .wsi-steps{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:14px;counter-reset:s;}
  .wsi-steps li{display:flex;gap:12px;align-items:flex-start;}
  .wsi-steps i{flex:0 0 auto;width:28px;height:28px;border-radius:999px;background:var(--green);color:#fff;font-style:normal;font-weight:700;font-size:1.4rem;display:flex;align-items:center;justify-content:center;}
  .wsi-steps b{display:block;font-size:1.35rem;color:#fff;}
  .wsi-steps span{font-size:1.22rem;color:#8fa2ba;line-height:1.4;}
  @media (max-width:989px){
    .wsi-body{grid-template-columns:1fr;}
    .wsi-frow--2{grid-template-columns:1fr;}
    .wsi-needs{grid-template-columns:1fr;}
    .wsi-formcard{padding:20px 16px;}
  }
</style>

{% schema %}
{
  "name": "ESTRY Wholesale Inquiry",
  "settings": [
    {"type": "text", "id": "kicker", "label": "Kicker", "default": "B2B / Wholesale"},
    {"type": "text", "id": "heading", "label": "Heading", "default": "Bulk Battery Sourcing, Simplified"},
    {"type": "text", "id": "sub", "label": "Subtitle", "default": "Send your part list - get tier pricing, datasheets and compliance documents within 24 hours."}
  ],
  "presets": [{"name": "ESTRY Wholesale Inquiry"}]
}
{% endschema %}
"""

WHOLESALE_JS = r"""
<script>
(function(){
  var u=new URL(window.location);
  var md=document.getElementById('wsi-md');
  if(md){
    var s=u.searchParams.get('sku')||u.searchParams.get('m');
    if(s&&!md.value)md.value=s;
  }
  if(u.searchParams.get('need')==='certs'||u.searchParams.get('need')==='spec'){
    var boxes=document.querySelectorAll('.wsi-need input[type=checkbox]');
    if(boxes.length===4){boxes[0].checked=false;boxes[u.searchParams.get('need')==='certs'?2:1].checked=true;}
  }
})();
</script>
"""

CERTS = r"""{% comment %} estry-certificates-v1: compliance wall {% endcomment %}
<section class="crt">
  <div class="crt-hero">
    <div class="page-width">
      <p class="crt-hero__k">{{ section.settings.kicker | escape }}</p>
      <h1 class="crt-hero__t">{{ section.settings.heading | escape }}</h1>
      <p class="crt-hero__s">{{ section.settings.sub | escape }}</p>
    </div>
  </div>

  <div class="crt-body page-width">
    <div class="crt-grid">
      {%- for block in section.blocks -%}
      <div class="crt-card" {{ block.shopify_attributes }}>
        <div class="crt-card__badge">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M12 2 4 5v6c0 5 3.4 9.3 8 11 4.6-1.7 8-6 8-11V5l-8-3z"/><path d="m9 12 2 2 4-4"/></svg>
        </div>
        <h3 class="crt-card__t">{{ block.settings.title | escape }}</h3>
        <p class="crt-card__d">{{ block.settings.desc | escape }}</p>
      </div>
      {%- endfor -%}
    </div>

    <div class="crt-flow">
      <h2 class="crt-flow__t">Request a certificate in 3 steps</h2>
      <ol class="crt-steps">
        <li><i>1</i><div><b>Submit your models</b><span>List battery models or OEM part numbers via the inquiry form</span></div></li>
        <li><i>2</i><div><b>Verification (1 business day)</b><span>Our engineers match documents to your exact batch</span></div></li>
        <li><i>3</i><div><b>Receive by email</b><span>Signed PDFs, ready for customs and your compliance file</span></div></li>
      </ol>
      <a class="crt-cta" href="/pages/wholesale?need=certs">Request Certificates</a>
      <p class="crt-note">Certificates are issued per shipment batch and included free with every wholesale order. Retail customers: contact us with your order number.</p>
    </div>
  </div>
</section>

<style>
  .crt{--navy:#1B2A41;--green:#00A651;--green-d:#008A43;--line:#D9E2EC;--mut:#5A6B7F;}
  .crt-hero{background:linear-gradient(135deg,#1B2A41 0%,#243a57 60%,#16233a 100%);padding:40px 0 34px;color:#fff;text-align:center;}
  .crt-hero__k{margin:0 0 6px;font-size:1.2rem;letter-spacing:.14em;text-transform:uppercase;color:#9fd8b8;font-family:var(--font-heading-family);}
  .crt-hero__t{margin:0 0 10px;font-size:clamp(2.4rem,4vw,3.4rem);color:#fff;font-family:var(--font-heading-family);font-weight:var(--font-heading-weight);}
  .crt-hero__s{margin:0 auto;max-width:640px;font-size:1.5rem;color:#aebdd2;}
  .crt-body{padding:34px 0 56px;}
  .crt-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:18px;max-width:860px;margin:0 auto;}
  .crt-card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:24px 22px;transition:all .18s;position:relative;overflow:hidden;}
  .crt-card::before{content:"";position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,var(--green),#0dbd63);}
  .crt-card:hover{transform:translateY(-3px);box-shadow:0 14px 34px rgba(27,42,65,.13);border-color:#bfe5cf;}
  .crt-card__badge{width:52px;height:52px;border-radius:12px;background:#e7f5ed;color:var(--green-d);display:flex;align-items:center;justify-content:center;margin-bottom:14px;}
  .crt-card__badge svg{width:28px;height:28px;}
  .crt-card__t{margin:0 0 7px;font-size:1.7rem;color:var(--navy);font-family:var(--font-heading-family);font-weight:600;}
  .crt-card__d{margin:0;font-size:1.3rem;line-height:1.55;color:var(--mut);}
  .crt-flow{margin-top:44px;background:#fff;border:1px solid var(--line);border-radius:16px;padding:32px 34px;text-align:center;}
  .crt-flow__t{margin:0 0 24px;font-size:2.2rem;color:var(--navy);font-family:var(--font-heading-family);font-weight:600;}
  .crt-steps{list-style:none;margin:0 auto 26px;padding:0;display:grid;grid-template-columns:repeat(3,1fr);gap:18px;max-width:820px;text-align:left;}
  .crt-steps li{display:flex;gap:12px;align-items:flex-start;}
  .crt-steps i{flex:0 0 auto;width:30px;height:30px;border-radius:999px;background:var(--green);color:#fff;font-style:normal;font-weight:700;font-size:1.5rem;display:flex;align-items:center;justify-content:center;}
  .crt-steps b{display:block;font-size:1.4rem;color:var(--navy);margin-bottom:2px;}
  .crt-steps span{font-size:1.25rem;color:var(--mut);line-height:1.45;}
  .crt-cta{display:inline-block;background:var(--green);color:#fff;border-radius:10px;padding:14px 34px;font-size:1.6rem;font-weight:700;text-decoration:none;transition:background .15s;}
  .crt-cta:hover{background:var(--green-d);}
  .crt-note{margin:16px auto 0;max-width:640px;font-size:1.2rem;color:var(--mut);}
  @media (max-width:989px){
    .crt-grid{grid-template-columns:1fr;}
    .crt-steps{grid-template-columns:1fr;max-width:420px;}
    .crt-flow{padding:24px 18px;}
  }
</style>

{% schema %}
{
  "name": "ESTRY Certificates",
  "settings": [
    {"type": "text", "id": "kicker", "label": "Kicker", "default": "Compliance & Certification"},
    {"type": "text", "id": "heading", "label": "Heading", "default": "Battery Compliance Documents"},
    {"type": "text", "id": "sub", "label": "Subtitle", "default": "UN 38.3 test summaries and MSDS/SDS for every model - free with wholesale orders."}
  ],
  "blocks": [
    {"type": "cert", "name": "Certificate card", "settings": [
      {"type": "text", "id": "title", "label": "Title"},
      {"type": "textarea", "id": "desc", "label": "Description"}
    ]}
  ],
  "presets": [{"name": "ESTRY Certificates"}]
}
{% endschema %}
"""

CERT_CARDS = {
    "c1": {"title": "UN 38.3", "desc": "Mandatory air-transport safety testing (T.1-T.8: altitude, thermal cycling, vibration, shock, external short-circuit, impact/crush, overcharge, forced discharge). Test summary issued per battery family - included free with every wholesale shipment."},
    "c2": {"title": "MSDS / SDS", "desc": "Material Safety Data Sheet (16-section SDS) covering cell chemistry, composition, handling, storage, transport classification and first-aid measures. Accepted by forwarders and customs worldwide - provided per model on request."},
}


def get_asset(key):
    return c.request("GET", f"themes/{TID}/assets.json",
                     params={"asset[key]": key})["asset"]["value"]


def put_asset(key, value):
    c.request("PUT", f"themes/{TID}/assets.json",
              json_body={"asset": {"key": key, "value": value}})


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (estry-deploy)"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""


def upsert_page(handle, title, template, body):
    pages = c.request("GET", "pages.json", params={"handle": handle})["pages"]
    payload = {"title": title, "handle": handle, "body_html": body,
               "published": True, "template_suffix": template}
    if pages:
        pid = pages[0]["id"]
        payload["id"] = pid
        c.request("PUT", f"pages/{pid}.json", json_body={"page": payload})
        return f"updated id={pid}"
    r = c.request("POST", "pages.json", json_body={"page": payload})
    return f"created id={r['page']['id']}"


# ① sections
put_asset("sections/estry-wholesale.liquid", WHOLESALE + WHOLESALE_JS)
time.sleep(1)
assert "estry-wholesale-v2" in get_asset("sections/estry-wholesale.liquid")
print("[1] wholesale section uploaded")
put_asset("sections/estry-certificates.liquid", CERTS)
time.sleep(1)
assert "estry-certificates-v1" in get_asset("sections/estry-certificates.liquid")
print("[2] certificates section uploaded")

# ② 模板（证书模板带 6 张卡 blocks）
blocks, order = {}, []
for k, v in CERT_CARDS.items():
    blocks[k] = {"type": "cert", "settings": {"title": v["title"], "desc": v["desc"]}}
    order.append(k)
put_asset("templates/page.wholesale.json", json.dumps(
    {"sections": {"main": {"type": "estry-wholesale", "settings": {}}},
     "order": ["main"]}))
time.sleep(0.6)
put_asset("templates/page.certificates.json", json.dumps(
    {"sections": {"certs": {"type": "estry-certificates", "settings": {},
                            "blocks": blocks, "block_order": order}},
     "order": ["certs"]}))
time.sleep(1)
assert json.loads(get_asset("templates/page.wholesale.json"))["order"] == ["main"]
assert json.loads(get_asset("templates/page.certificates.json"))["order"] == ["certs"]
print("[3] templates uploaded")

# ③ 页面
print("[4] wholesale page", upsert_page(
    "wholesale", "Wholesale & Bulk Inquiry", "wholesale",
    "<p>B2B battery sourcing: send your part list and receive tier pricing, "
    "datasheets and compliance documents within 24 hours.</p>"))
print("[5] certificates page", upsert_page(
    "certificates", "Certificates & Compliance", "certificates",
    "<p>UN 38.3 test summaries and MSDS documentation for Estry replacement "
    "batteries - free with wholesale orders.</p>"))

# ④ 线上断言
time.sleep(6)
st, h = fetch("https://www.estrybattery.com/pages/wholesale?f=" + str(int(time.time())))
ok = st == 200 and "wsi-formcard" in h and "contact[" in h and "Send Inquiry" in h
print(f"[6] wholesale {st} form-rendered={ok}")
assert ok
st2, h2 = fetch("https://www.estrybattery.com/pages/certificates?f=" + str(int(time.time())))
ok2 = st2 == 200 and "crt-card" in h2 and "UN 38.3" in h2
print(f"[7] certificates {st2} cards-rendered={ok2}")
assert ok2
st3, h3 = fetch("https://www.estrybattery.com/pages/wholesale?sku=CS-ZBR138BX")
print(f"[8] prefill path {st3}")
assert st3 == 200

print("ADD-INQUIRY-CERT-DONE /pages/wholesale + /pages/certificates")

