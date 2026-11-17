# -*- coding: utf-8 -*-
"""Estry 电池规格书页 (B2B 四件套之二).

  1. 上传 sections/estry-spec-sheet.liquid (A4 文档版式+print CSS+?m=csid 渲染)
  2. 上传 templates/page.specification.json
  3. 创建/更新 /pages/specification
  4. 线上断言 (含样本型号渲染)
用法:
  sudo -u jason env HOME=/home/jason .venv/bin/python add_spec_sheet.py
"""
import json
import sys
import time
import urllib.request

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

TID = 190031036660
SEC_KEY = "sections/estry-spec-sheet.liquid"
TPL_KEY = "templates/page.specification.json"
c = ShopifyRest(StoreService().get_client(1)).client

SECTION = r"""{% comment %} estry-spec-sheet-v1: datasheet {% endcomment %}
<section class="sp" id="sp-root">
  <div class="sp-wrap page-width">
    <div class="sp-loading" id="sp-loading">Loading specification&hellip;</div>
    <div class="sp-notfound" id="sp-notfound" hidden>
      <div class="sp-nf-card">
        <h2 class="sp-nf-t">Model not found</h2>
        <p class="sp-nf-s">Check the battery model number (format: CS-XXXXXX), or search the full database:</p>
        <div class="sp-nf-row">
          <input id="sp-nf-q" class="sp-nf-input" type="text" placeholder="Enter model, e.g. CS-ZBR138BX">
          <button id="sp-nf-go" class="sp-nf-btn" type="button">Open Datasheet</button>
          <a class="sp-nf-alt" href="/pages/battery-search">Advanced search &rarr;</a>
        </div>
      </div>
    </div>

    <article class="sp-sheet" id="sp-sheet" hidden>
      <header class="sp-head">
        <div class="sp-head__brand">
          <span class="sp-head__logo">ESTRY<em>&#9889;</em></span>
          <span class="sp-head__org">Technical Datasheet</span>
        </div>
        <div class="sp-head__acts">
          <button class="sp-btn sp-btn--ghost" id="sp-print" type="button">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2M6 14h12v7H6z"/></svg>
            Print / PDF
          </button>
          <a class="sp-btn sp-btn--solid" id="sp-quote" href="/pages/wholesale">Bulk Quote</a>
          <a class="sp-btn sp-btn--ghost" id="sp-buy" href="#" target="_blank" rel="noopener">Buy 1 pc</a>
        </div>
      </header>
      <p class="sp-tier">Volume discounts at checkout &mdash; <b>10+ &minus;5%</b> &middot; <b>20+ &minus;6%</b> &middot; <b>50+ &minus;8%</b> &middot; <b>100+ &minus;10%</b><span> (cart total, mix &amp; match)</span></p>

      <div class="sp-title">
        <div>
          <div class="sp-title__cat" id="sp-cat"></div>
          <h1 class="sp-title__model" id="sp-model"></h1>
          <div class="sp-title__fit" id="sp-fitshort"></div>
        </div>
        <div class="sp-title__badges" id="sp-badges"></div>
      </div>

      <div class="sp-grid">
        <div class="sp-sec">
          <h3 class="sp-sec__t">Electrical Characteristics</h3>
          <table class="sp-tab" id="sp-elec"></table>
        </div>
        <div class="sp-sec">
          <h3 class="sp-sec__t">Mechanical &amp; Physical</h3>
          <table class="sp-tab" id="sp-mech"></table>
        </div>
      </div>

      <div class="sp-sec">
        <h3 class="sp-sec__t">OEM Replacement Part Numbers</h3>
        <div class="sp-chips" id="sp-pn"></div>
      </div>

      <div class="sp-sec">
        <h3 class="sp-sec__t">Compatible Device Models</h3>
        <div class="sp-chips" id="sp-fm"></div>
      </div>

      <div class="sp-sec">
        <h3 class="sp-sec__t">Compliance &amp; Certification</h3>
        <div class="sp-cert">
          <div class="sp-cert__row">
            <span class="sp-cert__b">UN 38.3</span><span class="sp-cert__d">Air transport safety test report &mdash; available on request</span>
            <span class="sp-cert__b">MSDS</span><span class="sp-cert__d">Material Safety Data Sheet &mdash; available on request</span>
          </div>
          <a class="sp-cert__lnk" href="/pages/certificates">Request certificates for this model &rarr;</a>
        </div>
      </div>

      <footer class="sp-foot">
        <div class="sp-foot__co">
          <b>ESTRY</b> &middot; Replacement Battery Solutions &middot; www.estrybattery.com
        </div>
        <p class="sp-foot__legal">This datasheet is provided for engineering reference. Specifications are typical values at 25&deg;C and may vary &plusmn;5%. Estry replacement batteries are manufactured to meet or exceed original OEM specifications. All OEM part numbers and device models listed are for cross-reference compatibility only; Estry is not affiliated with the OEM brands mentioned. Copyright &copy; <span id="sp-yr"></span> Estry. All rights reserved.</p>
      </footer>
    </article>
  </div>
</section>

<style>
  .sp{--navy:#1B2A41;--green:#00A651;--green-d:#008A43;--line:#D9E2EC;--line2:#E5EBF1;--mut:#5A6B7F;--bg:#EEF1F5;padding:26px 0 50px;background:var(--bg);}
  .sp-wrap{max-width:960px;margin:0 auto;}
  .sp-loading,.sp-notfound{padding:80px 0;text-align:center;color:var(--mut);font-size:1.5rem;}
  .sp-nf-card{max-width:560px;margin:0 auto;background:#fff;border:1px solid var(--line);border-radius:12px;padding:36px 30px;}
  .sp-nf-t{margin:0 0 8px;font-size:2.2rem;color:var(--navy);font-family:var(--font-heading-family);}
  .sp-nf-s{margin:0 0 18px;font-size:1.4rem;color:var(--mut);}
  .sp-nf-row{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;}
  .sp-nf-input{flex:1;min-width:200px;height:44px;border:1px solid var(--line);border-radius:8px;padding:0 14px;font-size:1.4rem;color:var(--navy);}
  .sp-nf-btn{height:44px;padding:0 18px;border:none;border-radius:8px;background:var(--green);color:#fff;font-size:1.4rem;font-weight:700;cursor:pointer;}
  .sp-nf-btn:hover{background:var(--green-d);}
  .sp-nf-alt{align-self:center;font-size:1.3rem;color:var(--green-d);margin-left:6px;}
  .sp-sheet{background:#fff;border:1px solid var(--line);border-radius:12px;box-shadow:0 10px 34px rgba(27,42,65,.10);padding:34px 40px 30px;}
  .sp-head{display:flex;justify-content:space-between;align-items:center;gap:14px;border-bottom:3px solid var(--navy);padding-bottom:14px;flex-wrap:wrap;}
  .sp-head__brand{display:flex;align-items:baseline;gap:12px;}
  .sp-head__logo{font-family:var(--font-heading-family);font-size:2.6rem;font-weight:700;color:var(--navy);letter-spacing:.04em;}
  .sp-head__logo em{font-style:normal;color:var(--green);font-size:2rem;}
  .sp-head__org{font-size:1.3rem;letter-spacing:.22em;text-transform:uppercase;color:var(--mut);border-left:2px solid var(--line);padding-left:12px;}
  .sp-head__acts{display:flex;gap:8px;flex-wrap:wrap;}
  .sp-tier{margin:10px 0 0;padding:8px 14px;border:1px solid #CBE7D6;background:#EDF7F1;border-radius:8px;font-size:1.25rem;color:#1B2A41;}
  .sp-tier b{color:#008A43;font-weight:700;}
  .sp-tier span{color:var(--mut);font-size:1.15rem;}
  .sp-btn{display:inline-flex;align-items:center;gap:6px;height:38px;padding:0 15px;border-radius:8px;font-size:1.3rem;font-weight:700;text-decoration:none;cursor:pointer;transition:all .15s;}
  .sp-btn svg{width:15px;height:15px;}
  .sp-btn--solid{background:var(--green);color:#fff;border:1.5px solid var(--green);}
  .sp-btn--solid:hover{background:var(--green-d);border-color:var(--green-d);}
  .sp-btn--ghost{background:#fff;color:var(--navy);border:1.5px solid var(--navy);}
  .sp-btn--ghost:hover{background:var(--navy);color:#fff;}
  .sp-title{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;padding:22px 0 6px;flex-wrap:wrap;}
  .sp-title__cat{font-size:1.3rem;letter-spacing:.16em;text-transform:uppercase;color:var(--green-d);font-weight:600;}
  .sp-title__model{margin:4px 0 6px;font-size:clamp(2.6rem,5vw,4rem);line-height:1;color:var(--navy);font-family:var(--font-heading-family);font-weight:600;}
  .sp-title__fit{font-size:1.4rem;color:var(--mut);max-width:560px;}
  .sp-title__badges{display:flex;gap:8px;flex-wrap:wrap;}
  .sp-badge{border:1.5px solid var(--line);border-radius:999px;padding:5px 14px;font-size:1.25rem;font-weight:600;color:var(--navy);background:#F8FAFC;}
  .sp-badge--g{border-color:#bfe5cf;background:#e7f5ed;color:var(--green-d);}
  .sp-grid{display:grid;grid-template-columns:1fr 1fr;gap:26px;margin-top:18px;}
  .sp-sec{margin-top:24px;}
  .sp-sec__t{margin:0 0 10px;font-size:1.5rem;color:var(--navy);font-family:var(--font-heading-family);letter-spacing:.08em;text-transform:uppercase;display:flex;align-items:center;gap:10px;font-weight:600;}
  .sp-sec__t::before{content:"";display:inline-block;width:5px;height:18px;background:var(--green);border-radius:2px;}
  .sp-tab{width:100%;border-collapse:collapse;font-size:1.35rem;color:#2A3B4F;border:1px solid var(--line2);}
  .sp-tab td{padding:8px 12px;border-bottom:1px solid var(--line2);}
  .sp-tab tr:last-child td{border-bottom:none;}
  .sp-tab td:first-child{width:44%;color:var(--mut);background:#F8FAFC;}
  .sp-tab td:last-child{font-weight:600;color:var(--navy);}
  .sp-chips{display:flex;flex-wrap:wrap;gap:7px;}
  .sp-chip{background:#F4F6F8;border:1px solid var(--line2);color:#2A3B4F;border-radius:6px;padding:5px 11px;font-size:1.28rem;font-family:ui-monospace,Menlo,Consolas,monospace;}
  .sp-chip--oem{background:#fff;border-color:#cfe8d9;color:var(--green-d);}
  .sp-cert{border:1px solid var(--line);border-radius:10px;padding:16px 18px;background:#F8FAFC;}
  .sp-cert__row{display:flex;flex-wrap:wrap;gap:10px 26px;}
  .sp-cert__b{font-weight:700;color:var(--navy);font-size:1.35rem;white-space:nowrap;}
  .sp-cert__d{color:var(--mut);font-size:1.3rem;flex:1;min-width:220px;}
  .sp-cert__lnk{display:inline-block;margin-top:12px;font-size:1.3rem;font-weight:600;color:var(--green-d);}
  .sp-foot{margin-top:30px;border-top:1px solid var(--line);padding-top:16px;}
  .sp-foot__co{font-size:1.35rem;color:var(--navy);margin-bottom:8px;}
  .sp-foot__co b{font-family:var(--font-heading-family);letter-spacing:.05em;}
  .sp-foot__legal{font-size:1.12rem;line-height:1.6;color:#8494a7;margin:0;}
  @media (max-width:749px){
    .sp-sheet{padding:22px 16px;}
    .sp-grid{grid-template-columns:1fr;}
    .sp{padding:14px 0 30px;}
    .sp-head__org{display:none;}
  }
  @media print{
    body *{visibility:hidden;}
    .sp,.sp *{visibility:visible;}
    .sp{background:#fff;padding:0;}
    .sp-sheet{box-shadow:none;border:none;border-radius:0;padding:10mm 8mm;max-width:100%;}
    .sp-head__acts,.sp-cert__lnk{display:none!important;}
    .sp-sec{break-inside:avoid;}
    .sp-title__model{font-size:26pt;}
  }
</style>
"""

JS_SCHEMA = r"""
<script>
(function(){
  var MANIFEST_URL = {{ 'spec-idx-manifest.json' | asset_url | json }};
  var SHARD_BASE = MANIFEST_URL.replace(/[^\/]*$/, '');
  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(ch){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];});}
  function row(k,v){return '<tr><td>'+k+'</td><td>'+(v!==''&&v!=null?v:'\u2014')+'</td></tr>';}
  function chips(el,arr,cls){
    el.innerHTML=(arr&&arr.length)?arr.map(function(x){return '<span class="sp-chip'+(cls||'')+'">'+esc(x)+'</span>';}).join(''):'<span class="sp-chip">\u2014</span>';
  }
  function render(it){
    document.getElementById('sp-loading').hidden=true;
    document.getElementById('sp-yr').textContent=new Date().getFullYear();
    var sheet=document.getElementById('sp-sheet');
    document.getElementById('sp-cat').textContent=[it.c,it.b].filter(Boolean).join(' \u00b7 ')||'Replacement Battery';
    document.getElementById('sp-model').textContent=it.m;
    document.getElementById('sp-fitshort').textContent=it.t||'';
    document.getElementById('sp-badges').innerHTML=
      (it.ch?'<span class="sp-badge sp-badge--g">'+esc(it.ch)+'</span>':'')+
      (it.cap?'<span class="sp-badge">'+esc(it.cap)+'</span>':'')+
      (it.v?'<span class="sp-badge">'+esc(it.v)+'</span>':'')+
      (it.wh?'<span class="sp-badge">'+it.wh+'Wh</span>':'');
    document.getElementById('sp-elec').innerHTML=
      row('Battery Model',esc(it.m))+
      row('Nominal Voltage',esc(it.v))+
      row('Nominal Capacity',esc(it.cap))+
      row('Rated Energy',it.wh?it.wh+' Wh':'')+
      row('Chemistry',esc(it.ch));
    document.getElementById('sp-mech').innerHTML=
      row('Dimensions',esc(it.d))+
      row('Net Weight',it.w?it.w+' g':'')+
      row('Category',esc(it.c))+
      row('Fits Brand',esc(it.b))+
      row('Unit Price (1 pc)',it.p!=null?'$'+it.p.toFixed(2)+' \u2014 lower at volume':'');
    chips(document.getElementById('sp-pn'),it.pn,' sp-chip--oem');
    chips(document.getElementById('sp-fm'),it.fm);
    document.getElementById('sp-quote').href='/pages/wholesale?sku='+encodeURIComponent(it.m);
    var buy=document.getElementById('sp-buy');
    if(it.h){buy.href='/products/'+it.h;}else{buy.style.display='none';}
    document.title=it.m+' \u2014 Specification Sheet | Estry';
    sheet.hidden=false;
  }
  function notfound(){
    document.getElementById('sp-loading').hidden=true;
    document.getElementById('sp-notfound').hidden=false;
  }
  function load(m){
    fetch(MANIFEST_URL).then(function(r){return r.json();}).then(function(mm){
      return Promise.all((mm.shards||[]).map(function(s){return fetch(SHARD_BASE+s).then(function(r){return r.json();});}));
    }).then(function(arr){
      for(var i=0;i<arr.length;i++){
        for(var j=0;j<arr[i].length;j++){
          if(arr[i][j].m===m){render(arr[i][j]);return;}
        }
      }
      notfound();
    }).catch(notfound);
  }
  document.getElementById('sp-print').onclick=function(){window.print();};
  var go=function(){
    var m=document.getElementById('sp-nf-q').value.trim().toUpperCase();
    if(!m)return;
    if(m.indexOf('CS-')!==0)m='CS-'+m;
    var u=new URL(window.location);u.searchParams.set('m',m);
    window.history.replaceState(null,'',u);
    document.getElementById('sp-notfound').hidden=true;
    document.getElementById('sp-loading').hidden=false;
    load(m);
  };
  document.getElementById('sp-nf-go').onclick=go;
  document.getElementById('sp-nf-q').addEventListener('keydown',function(e){if(e.key==='Enter')go();});
  var m=new URL(window.location).searchParams.get('m');
  if(m&&/^[A-Za-z0-9-]+$/.test(m))load(m.toUpperCase());else notfound();
})();
</script>

{% schema %}
{
  "name": "ESTRY Spec Sheet",
  "settings": [],
  "presets": [{"name": "ESTRY Spec Sheet"}]
}
{% endschema %}
"""

TPL = json.dumps({
    "sections": {"spec": {"type": "estry-spec-sheet", "settings": {}}},
    "order": ["spec"]})


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


# ① section + ② 模板
put_asset(SEC_KEY, SECTION + JS_SCHEMA)
time.sleep(1)
assert "estry-spec-sheet-v1" in get_asset(SEC_KEY), "section readback failed"
print("[1] section uploaded:", SEC_KEY)
put_asset(TPL_KEY, TPL)
time.sleep(1)
assert json.loads(get_asset(TPL_KEY))["order"] == ["spec"]
print("[2] template uploaded:", TPL_KEY)

# ③ 页面（幂等）
pages = c.request("GET", "pages.json", params={"handle": "specification"})["pages"]
body = ("<p>Official Estry battery specification sheets: electrical characteristics, "
        "mechanical drawings, OEM cross-reference and compliance documents for every "
        "replacement battery model. Printable A4 datasheet, bulk quote on request.</p>")
if pages:
    pid = pages[0]["id"]
    c.request("PUT", f"pages/{pid}.json", json_body={"page": {
        "id": pid, "title": "Specification Sheets", "handle": "specification",
        "body_html": body, "published": True, "template_suffix": "specification"}})
    print(f"[3] page updated id={pid}")
else:
    r = c.request("POST", "pages.json", json_body={"page": {
        "title": "Specification Sheets", "handle": "specification",
        "body_html": body, "published": True, "template_suffix": "specification"}})
    print(f"[3] page created id={r['page']['id']}")

# ④ 线上断言（页面 + 样本型号参数路径）
time.sleep(6)
base = "https://www.estrybattery.com/pages/specification"
st, html = fetch(base + "?f=" + str(int(time.time())))
ok = st == 200 and "sp-sheet" in html and "spec-idx-manifest.json" in html \
     and "Technical Datasheet" in html
print(f"[4] page {st} datasheet-skeleton={ok}")
assert ok
st2, h2 = fetch(base + "?m=CS-ZBR138BX&f=" + str(int(time.time())))
print(f"[5] sample ?m=CS-ZBR138BX {st2} skeleton-ok={'sp-model' in h2}")
assert st2 == 200

print("ADD-SPEC-SHEET-DONE https://www.estrybattery.com/pages/specification?m=CS-ZBR138BX")

