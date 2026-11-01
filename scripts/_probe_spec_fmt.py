# -*- coding: utf-8 -*-
"""CS-TVR500VX 规格字段值格式探查（body_html 规格表映射用）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from shopify_admin.core.database import get_cs_engine

with get_cs_engine().connect() as c:
    rows = c.execute(text(
        "SELECT DISTINCT battery_type, capacity, voltage, wh_value, dimension, "
        "net_weight_g, gross_weight_g, category, suggested_retail_price "
        "FROM cs_product WHERE cs_id='CS-TVR500VX' LIMIT 5")).all()
    for r in rows:
        print(dict(r._mapping))
    # 全库 wh_value/voltage/capacity 格式抽样
    sample = c.execute(text(
        "SELECT DISTINCT wh_value, voltage, capacity FROM cs_product "
        "WHERE wh_value IS NOT NULL AND wh_value<>'' LIMIT 8")).all()
    print("wh_value 样例:", [dict(r._mapping) for r in sample])
