# -*- coding: utf-8 -*-
"""线上导航冒烟：新菜单生效 + 死入口消失。"""
import re
import urllib.request

req = urllib.request.Request("https://estrybattery.com/",
                             headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
print("首页长度:", len(html))

ids = sorted(set(re.findall(r'id="HeaderMenu-([^"]+)"', html)))
print("桌面导航项:", ids)

drawer = sorted(set(re.findall(r'id="HeaderDrawer-([^"]+)"', html)))
print("抽屉导航组:", drawer[:12])

bad = [k for k in ("phone-smartphone", "laptop-notebook", "umpc",
                   "pda-pocket", "camera", "gps-navigator", "ebook",
                   "survey-test", "battery-grip")
       if any(k in i for i in ids + drawer)]
print("残留死入口:", bad or "无")
