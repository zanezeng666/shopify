# -*- coding: utf-8 -*-
"""查 cs_user_info 可用客户号 + bmai_config 配置。"""
import sys

sys.path.insert(0, "/data/bmai/src")
from sqlalchemy import text  # noqa: E402
from bmai.core.database import cs_engine  # noqa: E402

eng = cs_engine.engine
with eng.connect() as c:
    cols = c.execute(text("SHOW COLUMNS FROM cs_user_info")).fetchall()
    print("cols:", [x[0] for x in cols])
    rows = c.execute(text(
        "SELECT rcustomerno, cs_username, LENGTH(cs_password) FROM cs_user_info LIMIT 5")).fetchall()
    for r in rows:
        print("user:", r)
    try:
        cfg = c.execute(text(
            "SELECT config_key, LEFT(config_value, 40) FROM bmai_config "
            "WHERE config_key LIKE '%rcustomer%' OR config_key LIKE '%customerno%'")).fetchall()
        print("config:", cfg)
    except Exception as e:
        print("cfg err:", str(e)[:120])
