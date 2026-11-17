# -*- coding: utf-8 -*-
"""探 wholesale/specification 页表单现状 + 产品页询盘入口现状。"""
import re
import urllib.request


def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")


for u in ["https://www.estrybattery.com/pages/wholesale",
          "https://www.estrybattery.com/pages/certificates"]:
    h = get(u)
    print("==", u, "bytes", len(h))
    print(" form:", len(re.findall(r"<form[^>]*", h)),
          "contact_posted:", "contact_posted" in h,
          "textarea:", len(re.findall(r"<textarea", h)),
          "quote:", len(re.findall(r"[Qq]uote", h)))

# 产品页询盘入口现状
h = get("https://www.estrybattery.com/products/cs-ams723md-1")
print("== product page bytes", len(h))
print(" quote-btn:", len(re.findall(r"[Qq]uote", h)),
      "wholesale-link:", len(re.findall(r"/pages/wholesale", h)))
