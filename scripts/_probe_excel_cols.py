# -*- coding: utf-8 -*-
"""小批量 CIM 导出，查看 Excel 全部原始列（找类目 ID）。"""
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from openpyxl import load_workbook

from bmai.supply_chain.cs_supplier import CIMClient
from shopify_admin.config.settings import settings

client = CIMClient(settings.bmai_rcustomerno)
excel = client.products.export_products_by_ids(["CS-AYD1CL", "CS-TMS20SL"])
client.close()
ws = load_workbook(BytesIO(excel), read_only=True).active
rows = list(ws.iter_rows(values_only=True))
print(f"rows={len(rows)} cols={ws.max_column}")
for i, r in enumerate(rows[:4]):
    print(f"--- row{i}")
    for j, x in enumerate(r):
        if x is not None and str(x).strip():
            print(f"  col{j}: {str(x)[:70]}")
