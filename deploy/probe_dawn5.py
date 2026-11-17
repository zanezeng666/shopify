"""基线钉死：shopifypreview 签名链接 ± preview_theme_id 的渲染对比（main vs Dawn）。"""
import re
import subprocess

U = "https://44brxf6v53ppzorm-5953192036.shopifypreview.com/products_preview?preview_key=e799d6e99dde457735db8e7c4fe5386e"

for tag, url in (("A main", U), ("B dawn", U + "&preview_theme_id=190031036660")):
    r = subprocess.run(["curl", "-skL", "-m", "60", "-w", "\n%{http_code}", url],
                       capture_output=True, text=True, timeout=75)
    body, _, code = r.stdout.rpartition("\n")
    fonts = sorted(set(re.findall(r"(assistant|oswald|inter)_n\d", body)))
    print(f"{tag}: {code} | {len(body)}B | ld+json: {body.count('application/ld+json')}"
          f" | fonts: {fonts}")
    print(f"   spec-table: {'Specification</h3>' in body} | FAQ-details: {'<details' in body}"
          f" | entity: {'This is a' in body}")
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', body, re.S):
        t = re.search(r'"@type"\s*:\s*"(\w+)"', m.group(1))
        print("   ld type:", t.group(1) if t else "?")
