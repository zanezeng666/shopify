# -*- coding: utf-8 -*-
"""抓隐私政策页正文 + 首页用途说明现状。"""
import re
import urllib.request

req = urllib.request.Request(
    "https://www.estrybattery.com/policies/privacy-policy",
    headers={"User-Agent": "Mozilla/5.0"})
t = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
m = re.search(r"<main.*?</main>", t, re.S)
body = m.group(0) if m else t
txt = re.sub(r"<[^>]+>", " ", body)
txt = re.sub(r"\s+", " ", txt).strip()
print("政策页正文字符数:", len(txt))
print("开头:", txt[:300])

req2 = urllib.request.Request(
    "https://www.estrybattery.com/", headers={"User-Agent": "Mozilla/5.0"})
h = urllib.request.urlopen(req2, timeout=15).read().decode("utf-8", "ignore")
print("\n首页 title:", re.search(r"<title>(.*?)</title>", h, re.S).group(1)[:100])
print("首页 meta描述:",
      (re.search(r'name="description" content="([^"]{0,160})', h) or ["", ""])[1])
print("首页含 privacy 链接:",
      len(re.findall(r'href="[^"]*(?:privacy|policies)[^"]*"', h)), "个")
for x in set(re.findall(r'href="([^"]*(?:privacy|policies)[^"]*)"', h)):
    print("  ", x)
