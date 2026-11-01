# -*- coding: utf-8 -*-
"""老库订单数据形态取样。"""
import sys

sys.path.insert(0, "src")

from sqlalchemy import text

from shopify_admin.core.database import get_legacy_engine

eng = get_legacy_engine()
with eng.connect() as c:
    print("--- store_info 样本:")
    for r in c.execute(text(
        "SELECT api_key, domain, username, is_available, Rcustomerno, main_ship_by, "
        "ship_of_country_first, is_inventory_available FROM shopify_store_info LIMIT 3"
    )):
        print("  ", str(r)[:200])

    print("--- order_id 形态:")
    for r in c.execute(text(
        "SELECT order_id, order_item_id, status, store_name, order_date FROM orders_report ORDER BY order_date DESC LIMIT 5"
    )):
        print("  ", str(r)[:180])

    print("--- status 值域:")
    for r in c.execute(text("SELECT status, COUNT(*) FROM orders_report GROUP BY status")):
        print("  ", tuple(r))

    print("--- ship_platform/ship_by/warehouse 值域:")
    for r in c.execute(text(
        "SELECT ship_platform, ship_by, warehouse_name, COUNT(*) FROM orders_report "
        "GROUP BY ship_platform, ship_by, warehouse_name LIMIT 15"
    )):
        print("  ", tuple(r))

    print("--- 单订单行项聚合形态:")
    for r in c.execute(text(
        "SELECT order_id, COUNT(*), MIN(order_date), MAX(purchase_date) FROM orders_report "
        "GROUP BY order_id ORDER BY COUNT(*) DESC LIMIT 5"
    )):
        print("  ", tuple(r))
