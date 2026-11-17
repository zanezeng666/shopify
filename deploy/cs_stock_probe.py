# -*- coding: utf-8 -*-
"""探查 CS 库存数据结构：表、字段、是否有历史快照。"""
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv("/home/jason/shopify-admin/.env")
url = os.environ.get("SOURCE_DB_URL") or os.environ.get("DB_URL")
if not url:
    # 从项目的 database 配置读
    import sys
    sys.path.insert(0, "/home/jason/shopify-admin")
    from shopify_admin.core.database import get_engine
    eng = get_engine()
else:
    eng = create_engine(url)

with eng.connect() as c:
    # 找 cs_ 和库存相关表
    rows = c.execute(text(
        "SELECT table_name, table_rows FROM information_schema.tables "
        "WHERE table_schema = DATABASE() "
        "AND (table_name LIKE 'cs_%' OR table_name LIKE '%stock%' "
        "OR table_name LIKE '%snapshot%' OR table_name LIKE '%invent%') "
        "ORDER BY table_name")).fetchall()
    print("=== 相关表 ===")
    for t, n in rows:
        print(f"  {t} (~{n}行)")
    # cs_product 字段
    cols = c.execute(text(
        "SELECT column_name, column_type FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = 'cs_product' "
        "ORDER BY ordinal_position")).fetchall()
    print("\n=== cs_product 字段 ===")
    for name, typ in cols:
        print(f"  {name} {typ}")
