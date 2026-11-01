# -*- coding: utf-8 -*-
"""确认 cs_new 运费表在位 + 抽样 zone/费率/carrier"""
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine

with get_cs_engine().connect() as c:
    for t in ("cs_shipping_carrier", "cs_shipping_rate", "cs_shipping_zone"):
        n = c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(t, n)
    print("carriers:", c.execute(text(
        "SELECT carrier_code, carrier_name, origin, destination, is_active "
        "FROM cs_shipping_carrier")).all())
    print("zones sample:", c.execute(text(
        "SELECT zone, COUNT(*) FROM cs_shipping_zone GROUP BY zone ORDER BY zone")).all())
    print("rate weights sample:", c.execute(text(
        "SELECT carrier_code, MIN(weight_g), MAX(weight_g), COUNT(DISTINCT weight_g) "
        "FROM cs_shipping_rate GROUP BY carrier_code")).all())
    print("rate sample:", c.execute(text(
        "SELECT * FROM cs_shipping_rate ORDER BY id LIMIT 5")).all())
