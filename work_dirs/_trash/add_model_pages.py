# -*- coding: utf-8 -*-
"""Estry 型号库 SEO 页 v1（programmatic landing pages）.

数据源: 主题资产 spec-idx-{0,1,2}.json (8752 型号)
策略: 第一批试点=Medical 类目 50 个（fm/pn 覆盖面优先），静态 body_html 渲染:
  H1 型号+设备名 / 规格表 / Fits 设备列表 / Buy+Spec CTA / FAQ / JSON-LD Product schema / 相关型号内链
page handle = 型号小写 slug (CS- 前缀天然防撞), Shopify sitemap 自动收录.
幂等: handle 已存在则跳过. 断点: /tmp/model_pages_done.txt.
用法:
  sudo -u jason env HOME=/home/jason .venv/bin/python add_model_pages.py [N]
"""
import html
import json
import re
import sys
import time
import urllib.request

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

TID = 190031036660
N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
DONE = "/tmp/model_pages_done.txt"
rest = ShopifyRest(StoreService().get_client(1)).client


def slug(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:120]


def esc(x):
    return html.escape(str(x if x is not None else ""), quote=True)


def render(it, related):
    m, t = it["m"], it.get("t") or it["m"]
    fm = it.get("fm") or []
    pn = it.get("pn") or []
    dims = it.get("d") or "—"
    w = it.get("w")
    rows = [
        ("Model No.", m),
        ("Fits", t),
        ("Capacity", it.get("cap") or "—"),
        ("Voltage", it.get("v") or "—"),
        ("Energy", f"{it['wh']}Wh" if it.get("wh") else "—"),
        ("Chemistry", it.get("ch") or "—"),
        ("Dimensions", dims),
        ("Weight", f"{w}g" if w else "—"),
        ("OEM Part No.", ", ".join(pn) if pn else "—"),
    ]
    trs = "".join(f'<tr><th scope="row">{esc(k)}</th><td>{esc(v)}</td></tr>' for k, v in rows)
    fm_html = ""
    if fm:
        chips = "".join(f"<li>{esc(x)}</li>" for x in fm[:40])
        more = f'<li class="emd-more">…and {len(fm)-40} more</li>' if len(fm) > 40 else ""
        fm_html = (
            '<section class="emd-sec"><h2>Compatible Devices</h2>'
            f'<ul class="emd-fm">{chips}{more}</ul></section>')
    rel_html = ""
    if related:
        lis = "".join(
            f'<li><a href="/pages/{slug(r["m"])}">{esc(r["m"])}</a>'
            f'<span class="emd-rel-t">{esc(r.get("t") or r["m"])}</span></li>'
            for r in related)
        rel_html = f'<section class="emd-sec"><h2>Related Batteries</h2><ul class="emd-rel">{lis}</ul></section>'
    price = it.get("p")
    buy = (f'<a class="emd-btn emd-btn--buy" href="/products/{esc(it["h"])}">'
           f'Buy Now — ${price:.2f}</a>') if price else f'<a class="emd-btn emd-btn--buy" href="/products/{esc(it["h"])}">Buy Now</a>'
    spec = f'<a class="emd-btn emd-btn--spec" href="/pages/specification?m={urllib.request.quote(m)}">Full Spec Sheet</a>'
    faqs = [
        ("Is this battery compatible with my device?",
         f"The {esc(m)} is a replacement battery for {esc(t)}. "
         + ("See the compatible device list above for verified fits. " if fm else "")
         + "Match your original battery's model or OEM part number before ordering."),
        ("What certifications does this battery have?",
         "All Estry batteries ship with UN 38.3 transport certification and MSDS/SDS documentation, "
         "required for compliant air and ground shipping."),
        ("Do you offer wholesale pricing?",
         "Yes — volume discounts apply automatically: 5% off at 10+, 6% at 20+, 8% at 50+, and 10% at 100+ pieces. "
         "US shipping is free on every order."),
    ]
    faq_schema = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
        ensure_ascii=False)
    prod_schema = json.dumps({
        "@context": "https://schema.org", "@type": "Product",
        "name": f"{m} Battery Replacement",
        "description": f"Replacement battery for {t}. {it.get('cap') or ''} {it.get('v') or ''} "
                       f"{it.get('ch') or ''} battery by Estry.",
        "sku": m,
        "brand": {"@type": "Brand", "name": "Estry"},
        **({"offers": {"@type": "Offer", "price": f"{price:.2f}", "priceCurrency": "USD",
                       "url": f"https://www.estrybattery.com/products/{it['h']}"}} if price else {}),
    }, ensure_ascii=False)
    faq_html = "".join(
        f'<details class="emd-faq"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in faqs)
    body = f"""<style>
.emd-wrap{{max-width:76rem;margin:0 auto;}}
.emd-grid{{display:grid;grid-template-columns:1.2fr .8fr;gap:2.4rem;align-items:start}}
@media(max-width:749px){{.emd-grid{{grid-template-columns:1fr}}}}
.emd-card{{background:rgba(0,0,0,.02);border:1px solid rgba(0,0,0,.08);border-radius:10px;padding:1.6rem}}
.emd-card table{{width:100%;border-collapse:collapse;font-size:1.4rem}}
.emd-card th{{text-align:left;padding:.5rem .8rem .5rem 0;color:rgba(var(--color-foreground-rgb),.6);font-weight:600;white-space:nowrap;vertical-align:top}}
.emd-card td{{padding:.5rem 0;font-weight:500}}
.emd-card tr+tr{{border-top:1px solid rgba(0,0,0,.06)}}
.emd-price{{display:flex;align-items:baseline;gap:.6rem;margin:0 0 1.2rem}}
.emd-price b{{font-size:2.6rem}}
.emd-price span{{color:rgba(var(--color-foreground-rgb),.55);font-size:1.4rem}}
.emd-btn{{display:inline-flex;align-items:center;justify-content:center;padding:1rem 2rem;border-radius:8px;text-decoration:none;font-weight:600;font-size:1.5rem}}
.emd-btn--buy{{background:#01448D;color:#fff}}
.emd-btn--spec{{border:1.5px solid #01448D;color:#01448D;margin-top:.8rem}}
.emd-usp{{list-style:none;margin:1.6rem 0 0;padding:0;font-size:1.35rem;color:rgba(var(--color-foreground-rgb),.75)}}
.emd-usp li{{padding:.25rem 0 .25rem 1.6rem;position:relative}}
.emd-usp li:before{{content:"✓";position:absolute;left:0;color:#84C227;font-weight:700}}
.emd-sec{{margin-top:2.8rem}}
.emd-sec h2{{font-size:1.8rem;margin:0 0 1rem}}
.emd-fm{{columns:2;column-gap:2rem;margin:0;padding-left:1.2rem;font-size:1.35rem}}
@media(max-width:749px){{.emd-fm{{columns:1}}}}
.emd-fm li{{padding:.15rem 0;break-inside:avoid}}
.emd-rel{{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(22rem,1fr));gap:1rem}}
.emd-rel li{{border:1px solid rgba(0,0,0,.08);border-radius:8px;padding:.9rem 1.1rem}}
.emd-rel a{{font-weight:600;text-decoration:none}}
.emd-rel-t{{display:block;font-size:1.25rem;color:rgba(var(--color-foreground-rgb),.6);margin-top:.2rem}}
.emd-faq{{border:1px solid rgba(0,0,0,.08);border-radius:8px;padding:1rem 1.2rem;margin-bottom:.8rem}}
.emd-faq summary{{font-weight:600;cursor:pointer;font-size:1.5rem}}
.emd-faq p{{margin:.8rem 0 0;font-size:1.4rem;color:rgba(var(--color-foreground-rgb),.75)}}
</style>
<div class="emd-wrap">
<div class="emd-grid">
<div>
<h1>{esc(m)} Battery Replacement</h1>
<p class="emd-lead">Premium replacement battery for {esc(t)}. {esc(it.get("cap") or "")} {esc(it.get("v") or "")} {esc(it.get("ch") or "")} — engineered to original specifications and certified for safe transport.</p>
<div class="emd-card"><table>{trs}</table></div>
{fm_html}
{rel_html}
</div>
<div class="emd-card">
<div class="emd-price"><b>${price:.2f}</b><span>per unit · free US shipping</span></div>
{buy}
{spec}
<ul class="emd-usp">
<li>Volume discounts from 10 pcs (up to 10% off)</li>
<li>UN 38.3 certified + MSDS/SDS provided</li>
<li>Free US shipping on every order</li>
<li>B2B invoicing &amp; wholesale support</li>
</ul>
</div>
</div>
<section class="emd-sec emd-faqs"><h2>FAQ</h2>{faq_html}</section>
</div>
<script type="application/ld+json">{prod_schema}</script>
<script type="application/ld+json">{faq_schema}</script>"""
    tt = t if len(t) <= 180 else t[:177].rsplit(" ", 1)[0] + "…"
    title = f"{m} Battery – {tt} Replacement"
    return title, body


def main():
    items = []
    for i in range(3):
        a = rest.request("GET", f"themes/{TID}/assets.json",
                         params={"asset[key]": f"assets/spec-idx-{i}.json"})["asset"]
        items.extend(json.loads(a.get("value") or "[]"))
    print("total items:", len(items))
    med = [it for it in items if it.get("c") == "Medical"]
    med.sort(key=lambda it: -(len(it.get("fm") or []) + len(it.get("pn") or [])))
    print("medical:", len(med))

    done = set()
    try:
        done = {l.strip() for l in open(DONE) if l.strip()}
    except FileNotFoundError:
        pass

    created = skipped = 0
    for it in med[:N]:
        h = slug(it["m"])
        if h in done:
            skipped += 1
            continue
        exists = rest.request("GET", "pages.json", params={"handle": h, "limit": 1}).get("pages", [])
        related = [r for r in med if r["m"] != it["m"]
                   and (r.get("b") == it.get("b") or r.get("ch") == it.get("ch"))][:4]
        title, body = render(it, related)
        if exists:
            pid = exists[0]["id"]
            rest.request("PUT", f"pages/{pid}.json", json_body={
                "page": {"id": pid, "title": title, "body_html": body, "published": True}})
            print("updated", h)
        else:
            try:
                rest.request("POST", "pages.json", json_body={
                    "page": {"title": title, "handle": h, "body_html": body, "published": True}})
                print("created", h)
            except Exception as e:
                print("FAIL", h, str(getattr(e, "details", ""))[:220])
                continue
        with open(DONE, "a") as f:
            f.write(h + "\n")
        created += 1
        time.sleep(0.6)
    print(f"done: created/updated={created} skipped={skipped}")

    # 抽一页线上断言
    if med:
        h = slug(med[0]["m"])
        for _ in range(6):
            try:
                htmltxt = urllib.request.urlopen(f"https://www.estrybattery.com/pages/{h}", timeout=15).read().decode()
                ok = med[0]["m"] in htmltxt and "application/ld+json" in htmltxt
                print("live check", h, "PASS" if ok else "CONTENT MISSING")
                break
            except Exception:
                time.sleep(10)


if __name__ == "__main__":
    main()
