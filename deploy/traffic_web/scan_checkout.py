"""结账模拟全量扫描 v2: 58 国完整地址 + 重量档验证。"""
import json
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)

Q = """
query O($in: DraftOrderAvailableDeliveryOptionsInput!) {
  draftOrderAvailableDeliveryOptions(input: $in) {
    availableShippingRates {
      handle title price { amount currencyCode }
    }
  }
}
"""

ADDR = {  # country -> (city, zip, province)
    "US": ("Los Angeles", "90001", "CA"), "GB": ("London", "E1 6AN", "England"),
    "DE": ("Berlin", "10115", "Berlin"), "FR": ("Paris", "75001", "IDF"),
    "AU": ("Sydney", "2000", "NSW"), "CA": ("Toronto", "M5H 2N2", "ON"),
    "JP": ("Tokyo", "100-0001", "Tokyo"), "BR": ("Sao Paulo", "01001-000", "SP"),
    "MX": ("Mexico City", "01000", "CMX"), "NL": ("Amsterdam", "1012", "NH"),
    "ES": ("Madrid", "28001", "MD"), "IT": ("Milano", "20121", "MI"),
    "SE": ("Stockholm", "11120", "Stockholm"), "NO": ("Oslo", "0150", "Oslo"),
    "PL": ("Warsaw", "00-001", "MZ"), "PT": ("Lisbon", "1100", "Lisboa"),
    "CZ": ("Prague", "11000", "Prague"), "HU": ("Budapest", "1051", "Budapest"),
    "RO": ("Bucharest", "010011", "Bucharest"), "BG": ("Sofia", "1000", "Sofia"),
    "HR": ("Zagreb", "10000", "Zagreb"), "SI": ("Ljubljana", "1000", "Ljubljana"),
    "SK": ("Bratislava", "81101", "Bratislava"), "LT": ("Vilnius", "01110", "Vilnius"),
    "LV": ("Riga", "LV-1001", "Riga"), "EE": ("Tallinn", "10111", "Harju"),
    "FI": ("Helsinki", "00100", "Uusimaa"), "AT": ("Vienna", "1010", "Vienna"),
    "BE": ("Brussels", "1000", "Brussels"), "CH": ("Zurich", "8001", "ZH"),
    "IE": ("Dublin", "D01", "Dublin"), "DK": ("Copenhagen", "1050", "Copenhagen"),
    "IL": ("Tel Aviv", "61000", "Tel Aviv"), "AE": ("Dubai", "00000", "Dubai"),
    "SA": ("Riyadh", "11564", "Riyadh"), "BH": ("Manama", "00000", "Capital"),
    "BY": ("Minsk", "220000", "Minsk"), "UA": ("Kyiv", "01001", "Kyiv"),
    "RS": ("Belgrade", "11000", "Belgrade"), "MD": ("Chisinau", "2001", "Chisinau"),
    "MT": ("Valletta", "VLT", "Valletta"), "CY": ("Nicosia", "1010", "Nicosia"),
    "LU": ("Luxembourg", "1111", "Luxembourg"), "GR": ("Athens", "10551", "Attica"),
    "KH": ("Phnom Penh", "12000", "Phnom Penh"), "KR": ("Seoul", "03030", "Seoul"),
    "KZ": ("Almaty", "050000", "Almaty"),
    "MY": ("Kuala Lumpur", "50000", "MY-14"),
    "PH": ("Manila", "1000", "PH-00"), "SG": ("Singapore", "048580", ""),
    "TH": ("Bangkok", "10100", "Bangkok"), "VN": ("Hanoi", "100000", "Hanoi"),
    "UZ": ("Tashkent", "100000", "Tashkent"),
    "PE": ("Lima", "15001", "PE-LIM"), "CL": ("Santiago", "8320000", "RM"),
    "CO": ("Bogota", "110111", "Cundinamarca"),
    "NZ": ("Wellington", "6011", "Wellington"), "RU": ("Moscow", "101000", "Moscow"),
}


def rates_for(vin, qty, country, tries=3):
    city, zc, prov = ADDR[country]
    sa = {"country": country, "city": city, "zip": zc,
          "address1": "123 Main St"}
    if prov:
        sa["province"] = prov
    for i in range(tries):
        try:
            r = client.graphql(Q, {"in": {
                "lineItems": [{"variantId":
                               f"gid://shopify/ProductVariant/{vin}",
                               "quantity": qty}],
                "shippingAddress": sa}})
            return r["draftOrderAvailableDeliveryOptions"][
                "availableShippingRates"]
        except Exception as e:
            if i == tries - 1:
                return {"ERR": str(e)[:100]}
            time.sleep(2)


# 找可售 variant
prods = client.request(
    "GET", "products.json?limit=30&fields=id,title,variants")
good = None
for p in prods.get("products", []):
    for v in p.get("variants", []):
        if v.get("inventory_quantity", 0) > 0:
            r = rates_for(v["id"], 1, "US")
            if r and not isinstance(r, dict) and r:
                good = v["id"]
                print(f"[可售] {p['title'][:34]} sku={v.get('sku')} "
                      f"weight={v.get('grams')}g")
                break
        if good:
            break
    if good:
        break
if not good:
    print("!! 无可售 variant")
    sys.exit(1)

# 全量单件扫描
print(f"\n== 全量扫描（单件 T1）==")
ok, empty, err = [], [], []
for c in sorted(ADDR):
    r = rates_for(good, 1, c)
    if isinstance(r, dict):
        err.append(c)
        print(f"{c}: ERR {r['ERR'][:70]}")
    elif r:
        ok.append(c)
        print(f"{c}: " + " | ".join(
            f"{x['title'][:34]}=${x['price']['amount']}" for x in r))
    else:
        empty.append(c)
        print(f"{c}: !!无运费选项")
    time.sleep(0.35)

print(f"\n汇总: 可结账 {len(ok)}/{len(ADDR)} 国 | 无选项 {empty or '无'} | "
      f"错误 {err or '无'}")

# 重量档: 3 件 / 6 件
for qty in (3, 6):
    print(f"\n== {qty} 件（重量档跳档验证）==")
    for c in ("US", "GB", "DE", "AU", "BR", "RU", "CO"):
        r = rates_for(good, qty, c)
        if isinstance(r, dict):
            print(f"{qty}件 {c}: ERR")
        else:
            print(f"{qty}件 {c}: " + (" | ".join(
                f"{x['title'][:34]}=${x['price']['amount']}"
                for x in r) or "空"))
