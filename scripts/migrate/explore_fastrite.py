# -*- coding: utf-8 -*-
"""探查 fast_rite 库表结构（FastRite 批量库存源调研）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from shopify_admin.config.settings import settings

url = URL.create(
    "mysql+pymysql",
    username=settings.fastrite_db_user,
    password=settings.fastrite_db_password,
    host=settings.fastrite_db_host,
    port=settings.fastrite_db_port,
    database=settings.fastrite_db_name,
    query={"charset": "utf8"},
)
eng = create_engine(url)
with eng.connect() as c:
    tabs = [r[0] for r in c.execute(text("SHOW TABLES"))]
    print("tables:", tabs)
    for t in tabs:
        cnt = c.execute(text(f"SELECT COUNT(*) FROM `{t}`")).scalar()
        print(f"--- {t}: rows={cnt}")
        if cnt and cnt < 200000:
            cols = [r[0] for r in c.execute(text(f"SHOW COLUMNS FROM `{t}`"))]
            print("    cols:", cols)
