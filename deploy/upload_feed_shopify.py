# -*- coding: utf-8 -*-
"""feed CSV 上传 Shopify Files (stagedUploadsCreate + fileCreate) 拿 CDN URL。"""
import csv
import json
import sys
import time

import httpx

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

SRC = "/home/jason/shopify-admin/deploy/feed/estry_feed.tsv"
DST = "/home/jason/shopify-admin/deploy/feed/estry_feed.csv"

with open(SRC, encoding="utf-8") as f:
    rows = list(csv.reader(f, delimiter="\t"))
with open(DST, "w", newline="", encoding="utf-8") as f:
    csv.writer(f, quoting=csv.QUOTE_ALL).writerows(rows)
size = len(json.dumps(rows)) and __import__("os").path.getsize(DST)
print(f"CSV 已生成: {size/1e6:.1f} MB, {len(rows)-1} 行")

cl = ShopifyRest(StoreService().get_client(1)).client
GQL = f"{cl._client.base_url}/graphql.json"

def gql(query, variables=None):
    r = cl._client.post(GQL, auth=cl._auth,
                        json={"query": query, "variables": variables or {}},
                        timeout=60)
    try:
        return r.json()
    except Exception:
        print("GQL非JSON:", r.status_code, r.text[:300])
        raise

pre = gql('{ files(first:1, query:"estry_feed.txt") { nodes {id fileStatus '
          '... on GenericFile {url} } } }')
try:
    pn = pre["data"]["files"]["nodes"][0] if pre.get("data") else None
    if pn and pn["fileStatus"] == "READY" and pn.get("url"):
        print("已有 READY 文件:", pn["url"])
        sys.exit(0)
except Exception:
    pass

r = gql("""
mutation staged($in: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $in) {
    stagedTargets { url resourceUrl parameters {name value} }
    userErrors {field message}
  }
}""", {"in": [{"filename": "estry_feed.txt",
              "mimeType": "text/plain",
              "resource": "FILE", "httpMethod": "PUT",
              "fileSize": str(size)}]})
if "data" not in r:
    print("GQL响应:", json.dumps(r, ensure_ascii=False)[:400])
    sys.exit(1)
t = r["data"]["stagedUploadsCreate"]
if t["userErrors"]:
    print("staged 错误:", t["userErrors"])
    sys.exit(1)
tg = t["stagedTargets"][0]
print("staged OK:", tg["url"][:60])

headers = {p["name"]: p["value"] for p in tg["parameters"]}
with open(SRC, "rb") as f:
    up = httpx.put(tg["url"], headers=headers, content=f, timeout=600)
print("PUT 状态:", up.status_code)

time.sleep(2)
r2 = gql("""
mutation fc($f: [FileCreateInput!]!) {
  fileCreate(files: $f) { files {id fileStatus} userErrors {field message} }
}""", {"f": [{"originalSource": tg["resourceUrl"],
              "contentType": "FILE"}]})
if "data" not in r2:
    print("fileCreate 错误:", json.dumps(r2, ensure_ascii=False)[:400])
    sys.exit(1)
fc = r2["data"]["fileCreate"]
print("fileCreate:", json.dumps(fc, ensure_ascii=False)[:300])
fid = fc["files"][0]["id"] if fc.get("files") else None

for i in range(20):
    time.sleep(3)
    q = gql("""{ files(first:5, sortKey: CREATED_AT, reverse: true) {
      nodes {id fileStatus ... on GenericFile {url} } } }""")
    if "data" not in q or not q["data"]["files"]["nodes"]:
        print("查询响应:", json.dumps(q, ensure_ascii=False)[:300])
        break
    for n in q["data"]["files"]["nodes"]:
        if "47266969616628" in n["id"]:
            print(f"状态: {n['fileStatus']} url: {n.get('url','')}")
            if n["fileStatus"] == "READY" and n.get("url"):
                print("\n>>> 最终 CDN URL:", n["url"])
                sys.exit(0)
    print("(等待处理...)")
