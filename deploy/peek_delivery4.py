# -*- coding: utf-8 -*-
"""收尾内省：location group / zone 输入 + DeliveryProfile 查询字段。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService

c = StoreService().get_client(1)

def intro(name: str, fields: bool = True) -> None:
    if fields:
        q = ('{ __type(name: "%s") { inputFields { name '
             'type { kind name ofType { kind name ofType { kind name } } } } } }' % name)
    else:
        q = '{ __type(name: "%s") { fields { name type { kind name ofType { kind name } } } } }' % name
    r = c.graphql(q) or {}
    t = r.get("__type")
    if not t:
        print(f"== {name}: 不存在\n")
        return
    print(f"== {name} ==")
    fl = t.get("inputFields") or t.get("fields") or []
    for f in fl:
        ty = f["type"]
        inner = ty.get("ofType") or {}
        inner2 = (inner.get("ofType") or {})
        print(f"  {f['name']}: {ty.get('kind')}<{ty.get('name')}>"
              f" -> {inner.get('kind')}<{inner.get('name')}>"
              f" -> {inner2.get('kind')}<{inner2.get('name')}>")
    print()

intro("DeliveryProfileLocationGroupInput")
intro("DeliveryZoneCreateInput")
intro("DeliveryZoneUpdateInput")
intro("DeliveryProfile", fields=False)   # 查询字段
intro("DeliveryZone", fields=False)      # 查询字段
