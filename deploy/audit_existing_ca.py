"""审计既有 compare_at_price 的折扣分布（只读），供总报告评估是否合理。"""
import json
from decimal import Decimal

prods = json.load(open("/tmp/ca_products.json"))
buckets = {"<0（倒挂）": 0, "0-10%": 0, "10-18%": 0, "18-25%": 0, "25-50%": 0, ">=50%（虚高）": 0}
worst, best = [], []
for p in prods:
    for vid, price, cap in p["variants"]:
        if not cap:
            continue
        if Decimal(cap) <= 0:
            buckets["<0（倒挂）"] += 1  # cap=0 脏数据归入倒挂
            continue
        d = 1 - Decimal(price) / Decimal(cap)
        k = ("<0（倒挂）" if d < 0 else "0-10%" if d < Decimal("0.10") else "10-18%"
             if d < Decimal("0.18") else "18-25%" if d < Decimal("0.25")
             else "25-50%" if d < Decimal("0.50") else ">=50%（虚高）")
        buckets[k] += 1
        if d >= Decimal("0.50") and len(worst) < 8:
            worst.append((vid.split("/")[-1], price, cap, f"{d:.0%}"))
print("既有锚价折扣分布:", buckets)
print("虚高样例:", worst)
