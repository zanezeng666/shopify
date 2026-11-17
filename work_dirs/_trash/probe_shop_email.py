# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, "src")
from shopify_admin.services.stores.service import StoreService
c = StoreService().get_client(1)
print("shop:", str(c.graphql("{shop{email}}"))[:150])
