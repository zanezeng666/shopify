# -*- coding: utf-8 -*-
"""FastRite 渠道最终活体冒烟：库存 + 真实单号状态。"""
import sys

sys.path.insert(0, "src")

from shopify_admin.channels.base import ChannelOrderRef  # noqa: E402
from shopify_admin.channels.fastrite import FastRiteChannel  # noqa: E402

ch = FastRiteChannel()

# 库存（老工程样例 SKU）
inv = ch.get_inventory("BM-DET400G01")
print(f"inventory BM-DET400G01: available={inv.available} warehouses={inv.raw['warehouses']}")

# 库存（库里有量的 SKU——从 stock_table 挑一个正库存的）
import pymysql  # noqa: E402

conn = pymysql.connect(
    host="gz-cdb-aq76i6tl.sql.tencentcdb.com", port=63698,
    user="root", password="Bomi@81001", database="fast_rite",
)
cur = conn.cursor()
cur.execute(
    "SELECT sku, whCode, productStockDtl_availableAmount FROM stock_table "
    "WHERE productStockDtl_availableAmount > 0 AND is_valid = 1 ORDER BY update_date_time DESC LIMIT 3"
)
for sku, wh, qty in cur.fetchall():
    i = ch.get_inventory(sku)
    print(f"inventory {sku}: api_available={i.available} (db {wh}={qty})")

cur.execute("SELECT outbound_order_no, status, logistics_track_no FROM outbound_order ORDER BY update_time DESC LIMIT 1")
no, st, trk = cur.fetchone()
conn.close()
print(f"latest order: {no} db_status={st} db_track={trk}")

st = ch.get_status(ChannelOrderRef(channel="fastrite", order_id=no))
print(f"api_status: {st.status} track={st.tracking_number} company={st.tracking_company} err={st.error_message[:60]}")
