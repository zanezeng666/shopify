import json, urllib.request, base64

env = {}
for line in open('/home/jason/shopify-admin/.env'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip().strip('"')

import pymysql
conn = pymysql.connect(host=env['SHOPIFY_DB_HOST'], port=int(env.get('SHOPIFY_DB_PORT', 3306)),
                       user=env['SHOPIFY_DB_USER'], password=env['SHOPIFY_DB_PASSWORD'],
                       database=env['SHOPIFY_DB_NAME'])
cur = conn.cursor()
cur.execute("select api_key, api_secret, domain from stores where id=1")
key, secret, domain = cur.fetchone()
print("domain:", domain, "| key_len:", len(key), "| secret_len:", len(secret or ''))

headers = {"Content-Type": "application/json"}
if secret:
    headers["Authorization"] = "Basic " + base64.b64encode(f"{key}:{secret}".encode()).decode()
    print("auth: basic (legacy private app)")
else:
    headers["X-Shopify-Access-Token"] = key
    print("auth: token (custom app)")

q = {"query": "{ shop { name plan { displayName partnerDevelopment shopifyPlus } } }"}
req = urllib.request.Request(f"https://{domain}.myshopify.com/admin/api/2025-01/graphql.json",
                             data=json.dumps(q).encode(), headers=headers)
print(urllib.request.urlopen(req, timeout=20).read().decode())
