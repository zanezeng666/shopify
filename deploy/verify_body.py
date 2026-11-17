import sys
sys.path.insert(0, '/home/jason/shopify-admin/src')
from shopify_admin.services.products.sync_shopify import CsShopifySyncService as S

# 场景1：有 fit 无 part_no → Part Number 段省略
b1 = S._build_body_html({"cs_id": "CS-T1", "brand": "Acme", "fit_model": "M1,M2", "part_no": "",
                         "capacity": "", "voltage": "", "battery_type": "", "dimension": "",
                         "net_weight_g": 0, "gross_weight_g": 0})
print("case1 PartNumber-omitted:", "Compatible Battery Part Number" not in b1)
print("case1 Model-multiline:", "<li><b>M1</b></li>" in b1 and "<li><b>M2</b></li>" in b1)

# 场景2：无 fit 无 part_no → 两段都省略
b2 = S._build_body_html({"cs_id": "CS-T2", "brand": "Acme", "fit_model": "", "part_no": "",
                         "capacity": "", "voltage": "", "battery_type": "", "dimension": "",
                         "net_weight_g": 0, "gross_weight_g": 0})
print("case2 both-omitted:", "Compatible Model" not in b2 and "Compatible Battery Part Number" not in b2)
print("case2 brand-kept:", "<li><b>Acme</b></li>" in b2)

# 场景3：多 part_no 逗号分隔 → 多行加粗
b3 = S._build_body_html({"cs_id": "CS-T3", "brand": "Acme", "fit_model": "X1", "part_no": "P11,P22,P33",
                         "capacity": "", "voltage": "", "battery_type": "", "dimension": "",
                         "net_weight_g": 0, "gross_weight_g": 0})
print("case3 pno-multiline:", all(f"<li><b>{p}</b></li>" in b3 for p in ("P11", "P22", "P33")))
