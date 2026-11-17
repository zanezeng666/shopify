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
import os

import pymysql  # noqa: E402

# 凭据走环境变量（本地 .env / 服务器环境注入），严禁硬编码入库
_dsn = os.environ.get("FASTRITE_DSN", "")
if not _dsn:
    raise SystemExit("请设置 FASTRITE_DSN=mysql://user:password@host:port/fast_rite（见 .env.example）")
_user, _rest = _dsn.split("://", 1)[1].split(":", 1)
_pass, _hostpart = _rest.rsplit("@", 1)
_host, _port_db = _hostpart.split(":", 1)
_port, _db = _port_db.split("/", 1)
conn = pymysql.connect(host=_host, port=int(_port), user=_user, password=_pass, database=_db)
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
