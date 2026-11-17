# -*- coding: utf-8 -*-
"""内省 DeliveryProfileLocationGroup 查询字段。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService

c = StoreService().get_client(1)
r = c.graphql('{ __type(name: "DeliveryProfileLocationGroup") '
              '{ fields { name type { kind name ofType { kind name ofType { kind name ofType { kind name } } } } } } }') or {}
for f in (r.get("__type") or {}).get("fields", []):
    ty = f["type"]
    i1 = ty.get("ofType") or {}
    i2 = i1.get("ofType") or {}
    i3 = i2.get("ofType") or {}
    print(f"  {f['name']}: {ty.get('kind')}<{ty.get('name')}> -> "
          f"{i1.get('kind')}<{i1.get('name')}> -> "
          f"{i2.get('kind')}<{i2.get('name')}> -> {i3.get('kind')}<{i3.get('name')}>")
