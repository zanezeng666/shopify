# -*- coding: utf-8 -*-
"""首页 hub 渲染复查."""
import sys
import time
import urllib.request

BASE = "https://www.estrybattery.com/"


def fetch(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (estry-deploy)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "ignore")


for i in range(4):
    st, h = fetch(f"{BASE}?_chk={int(time.time())}{i}")
    hit = "ebh-root" in h
    print(f"try{i}: {st} ebh-root={'YES' if hit else 'NO'} len={len(h)}")
    if hit:
        j = h.find("ebh__title")
        print("title-ctx:", h[j:j + 80])
        break
    time.sleep(20)
