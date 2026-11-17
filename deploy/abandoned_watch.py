# -*- coding: utf-8 -*-
"""每日弃购监控：拉近 7 天 abandoned checkouts 落盘摘要。

新弃购追加到 deploy/abandoned_report.log（日期/邮箱/金额/商品）。
crontab 每日 09:00。SMTP 配置后可扩展邮件提醒（shop.email）。
"""
import json
import sys
from datetime import datetime, timedelta

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

rest = ShopifyRest(StoreService().get_client(1)).client
since = datetime.utcnow() - timedelta(days=7)

rows = rest.request("GET", "checkouts.json", params={"limit": 250}).get("checkouts", [])
recent = [c for c in rows if c.get("created_at", "") >= since.strftime("%Y-%m-%d")]
out = []
for c in recent:
    items = ", ".join(li.get("title", "?")[:40] for li in c.get("line_items", [])[:3])
    out.append({"created": c.get("created_at"), "email": c.get("email"),
                "total": c.get("total_price"), "items": items,
                "url": (c.get("abandoned_checkout_url") or "")[:120]})

with open("/home/jason/shopify-admin/deploy/abandoned_report.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

line = f"[{datetime.now():%Y-%m-%d %H:%M}] abandoned_7d={len(out)} total=${sum(float(o['total'] or 0) for o in out):.2f}"
with open("/home/jason/shopify-admin/deploy/abandoned_report.log", "a") as f:
    f.write(line + "\n")
print(line)
for o in out:
    print(" ", o["created"][:16], o["email"], o["total"], o["items"][:60])
