# -*- coding: utf-8 -*-
"""侦察7(终极): change_event修正字段找MC + Content API authinfo 列MC账号。"""
import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}",
     "Content-Type": "application/json", "developer-token": "unused"}
CID = "7059800494"

# 1) Content API authinfo: 列出该 OAuth 身份可访问的全部 MC 账号
r = httpx.get("https://shoppingcontent.googleapis.com/content/v2.1/"
              "accounts/authinfo", headers=H, timeout=30)
print("== authinfo ==", r.status_code)
if r.status_code == 200:
    d = r.json()
    for meth in d.get("accountManagementAccess", []) or []:
        gm = meth.get("grantedAccounts") or []
        print(" 授权账号数:", len(gm))
        for g in gm[:10]:
            print("  MC ID:", g.get("id"), "名:", g.get("name"))
else:
    print(" ", r.text[:160])

# 2) change_event 修正字段 (ADDED 事件在 python 侧过滤)
q = ("SELECT change_event.change_date_time, change_event.new_resource, "
     "change_event.change_operator_type FROM change_event "
     f"WHERE change_event.resource_name = "
     f"'customers/{CID}/campaigns/17557725557' "
     "AND change_event.change_date_time >= "
     "'2026-10-09 00:00:00.000000'")
r2 = httpx.post(
    f"https://googleads.googleapis.com/v25/customers/{CID}/"
    "googleAds:searchStream", headers=H, json={"query": q}, timeout=30)
rows = r2.json() if isinstance(r2.json(), list) else [r2.json()]
print("\n== change_event ==")
for b in rows:
    if "error" in b:
        print(" ERR:", b["error"]["details"][0]["errors"][0]
              ["message"][:150])
        continue
    for e in b.get("results", []):
        ce = e["changeEvent"]
        try:
            nr = json.loads(ce.get("newResource") or "{}")
        except Exception:
            nr = {}
        ss = nr.get("shoppingSetting", {})
        print(f" {ce.get('changeDateTime')} {ce.get('changeOperatorType')}"
              f" MC={ss.get('merchantCenterId')}")
