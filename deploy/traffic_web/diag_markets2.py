"""深挖 Market.conditions 提取各市场国家清单，对照 31 失败国。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)


def gql(q, vars=None):
    r = client.graphql(q, vars) if vars else client.graphql(q)
    return r


def leaf_type(t):
    while t.get("ofType"):
        t = t["ofType"]
    return t.get("kind"), t.get("name")


# 1) 找 conditions 字段的类型名
tm = gql('{ __type(name: "Market") { fields { name type { kind name ofType { kind name ofType { kind name } } } } } }')
cond_type = None
for f in tm["__type"]["fields"]:
    if f["name"] == "conditions":
        kind, cond_type = leaf_type(f["type"])
        print(f"conditions: kind={kind} type={cond_type}")

if not cond_type:
    print("未找到 conditions 类型")
    sys.exit(1)

# 2) 自省该类型字段
sub = gql(f'{{ __type(name: "{cond_type}") {{ fields {{ name type {{ kind name ofType {{ kind name ofType {{ kind name }} }} }} }} }} }}')
sfields = sub["__type"]["fields"]
print(f"{cond_type} 字段:", [f["name"] for f in sfields])

# 3) 找国家字段（可能是 [CountryCode!]! 枚举列表或对象列表）
sel = None
for f in sfields:
    if "countr" in f["name"].lower():
        kind, tname = leaf_type(f["type"])
        print(f"国家字段 {f['name']}: kind={kind} type={tname}")
        if kind == "ENUM" or kind == "SCALAR":
            sel = (f["name"], None)
        elif kind == "OBJECT" and tname:
            ss = gql(f'{{ __type(name: "{tname}") {{ fields {{ name }} }} }}')
            ssubs = [x["name"] for x in ss["__type"]["fields"]]
            print("  子字段:", ssubs)
            for c in ("code", "countryCode", "isoCode"):
                if c in ssubs:
                    sel = (f["name"], c)
                    break

if not sel:
    print("!! conditions 内未找到国家字段")
    sys.exit(1)

fname, cfield = sel
inner = fname if not cfield else f"{fname} {{ {cfield} }}"
q = "{ markets(first: 20) { nodes { id handle name enabled type conditions { %s } } } }" % inner
mc = gql(q)
all_codes = set()
for m in mc["markets"]["nodes"]:
    conds = m["conditions"]
    raw = conds[fname]
    if cfield:
        codes = sorted({r[cfield] for r in raw})
    else:
        codes = sorted(set(raw))
    all_codes |= set(codes)
    print(f'\n[{m["name"]}] type={m.get("type")} enabled={m["enabled"]} '
          f'countries={len(codes)}: {",".join(codes)}')

print(f"\n市场覆盖国家总数: {len(all_codes)}")
bad = ("BR CH CL CO CY DK EE ES FI FR HU IE LT LU LV MD MT MY NL NO NZ "
       "PE PH PL PT RO RS SE SI SK UA").split()
missing = [c for c in bad if c not in all_codes]
print(f"31 失败国不在任何市场: {len(missing)} -> {missing}")
