# -*- coding: utf-8 -*-
import shopify_admin.api.app as m

print("app module:", m.__file__)
print("total routes:", len(m.app.routes))
for r in m.app.routes:
    methods = sorted(getattr(r, "methods", []) or [])
    print(f"  {methods} {getattr(r, 'path', r)}")
