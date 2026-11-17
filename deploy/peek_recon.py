import json
b = json.load(open("/tmp/cat_brands.json"))
for cat, brands in b.items():
    print(cat, "|", ", ".join(f"{x}:{n}" for x, n in brands[:5]))
print("====COLLS====")
c = json.load(open("/tmp/colls.json"))
for h, t in c.items():
    print(h, "|", t)
