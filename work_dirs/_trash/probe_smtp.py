# -*- coding: utf-8 -*-
"""探 SMTP 配置（bmai）+ shop.email + shopify_admin 邮件能力。"""
import sys

sys.path.insert(0, "/data/bmai/src")
from bmai.config.store import ConfigStore  # noqa: E402
from bmai.config.settings import settings  # noqa: E402

print("smtp settings attrs:", {k: getattr(settings, k) for k in dir(settings)
                               if "smtp" in k.lower() or "mail" in k.lower()})
try:
    st = ConfigStore()
    for key in ["smtp_host", "smtp_port", "smtp_user", "smtp_from"]:
        try:
            v = st.get(key)
            print(key, "=", (v[:6] + "...") if v and len(str(v)) > 10 else v)
        except Exception as e:
            print(key, "err", str(e)[:80])
except Exception as e:
    print("store err:", str(e)[:120])

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
client = StoreService().get_client(1)
r = client.graphql("{shop{email senderEmail{email} staffAccounts(first:1){edges{node{email}}}}}")
print("shop:", str(r)[:220])
