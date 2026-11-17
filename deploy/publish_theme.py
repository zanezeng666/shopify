"""发布 ESTRY Dawn 为 main 主题；预置一键回滚脚本；确认角色切换。"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

NEW, OLD = 190031036660, 136764817652
c = ShopifyRest(StoreService().get_client(1)).client

ROLLBACK_SRC = '''"""一键回滚：切回旧主题 Buy on Amazon Simple。"""
import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest
c = ShopifyRest(StoreService().get_client(1)).client
c.request("PUT", "themes/{OLD}.json", json_body={"theme": {"id": {OLD}, "role": "main"}})
for t in c.request("GET", "themes.json")["themes"]:
    if t["id"] in ({NEW}, {OLD}):
        print(t["id"], t["role"], t["name"])
'''.replace("{OLD}", str(OLD)).replace("{NEW}", str(NEW))
with open("/tmp/rollback_theme.py", "w") as f:
    f.write(ROLLBACK_SRC)
print("rollback script ready: /tmp/rollback_theme.py")

c.request("PUT", f"themes/{NEW}.json",
          json_body={"theme": {"id": NEW, "role": "main"}})
time.sleep(3)
for t in c.request("GET", "themes.json")["themes"]:
    if t["id"] in (NEW, OLD):
        print(t["id"], "|", t["role"], "|", t["name"])
