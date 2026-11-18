"""对比丢失 zone 国家的 rates 形状找规律。"""
import json

p = json.load(open("/home/jason/traffic-web/cfg_shipping/plan.json"))
bad = {"US", "TH", "SG", "MY", "KZ", "KR", "KH", "JP"}
ok = {"VN", "AU", "DE", "GB", "CA", "MX", "BR", "PH", "NZ", "SG"}

print("BAD zones rates:")
for z in p["zones"]:
    c = z["countries"][0]
    if c in bad:
        print(f"  {c}: {[(r['price'], r['low_kg'], r['high_kg']) for r in z['rates']]}")
print("OK zones rates:")
for z in p["zones"]:
    c = z["countries"][0]
    if c in ok - bad:
        print(f"  {c}: {[(r['price'], r['low_kg'], r['high_kg']) for r in z['rates']]}")
