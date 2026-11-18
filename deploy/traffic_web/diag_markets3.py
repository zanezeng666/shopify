"""三 levels 深挖 regionsCondition -> regions -> countries { code }，
自适应连接式(connection)与对象式两种形态，汇总市场国家清单对照 31 失败国。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)


def gql(q):
    return client.graphql(q)


def leaf(t):
    while t.get("ofType"):
        t = t["ofType"]
    return t.get("kind"), t.get("name")


def fields_of(type_name):
    r = gql(
        "{ __type(name: \"%s\") { fields { name type { kind name ofType "
        "{ kind name ofType { kind name ofType { kind name } } } } } } }"
        % type_name)
    return r["__type"]["fields"]


# Level 0: MarketConditions.regionsCondition
mcf = fields_of("MarketConditions")
k0, t0 = leaf([f for f in mcf if f["name"] == "regionsCondition"][0]["type"])
fs1 = fields_of(t0)
print(f"{t0} 字段:", [f["name"] for f in fs1])

# Level 1: 找承载区域的列表字段
sel = None
for f in fs1:
    k, tn = leaf(f["type"])
    if k != "OBJECT" or not tn:
        continue
    f2s = fields_of(tn)
    names2 = [x["name"] for x in f2s]
    print(f"  {f['name']} -> {tn}: {names2}")
    # connection 形态: 取 nodes 元素类型继续
    inner_tn = tn
    if "nodes" in names2 and "edges" in names2:
        kn, inner_tn = leaf([x for x in f2s if x["name"] == "nodes"][0]["type"])
        f2s = fields_of(inner_tn)
        names2 = [x["name"] for x in f2s]
        print(f"    (connection) nodes -> {inner_tn}: {names2}")
    # 找 countries
    for x in f2s:
        if "countr" in x["name"].lower():
            k2, tn2 = leaf(x["type"])
            if k2 == "OBJECT" and tn2:
                f3s = fields_of(tn2)
                names3 = [y["name"] for y in f3s]
                print(f"      {x['name']} -> {tn2}: {names3}")
                for y in f3s:
                    if y["name"] in ("code", "countryCode", "isoCode"):
                        base = f["name"] + ("(first: 30) { nodes " if inner_tn != tn else " ")
                        # connection 需闭合 nodes
                        if base.endswith("nodes "):
                            sel = (f"regionsCondition {{ {f['name']}(first: 50) "
                                   f"{{ nodes {{ {x['name']} {{ {y['name']} }} }} }} }}",
                                   x["name"], y["name"])
                        else:
                            sel = (f"regionsCondition {{ {f['name']} "
                                   f"{{ {x['name']} {{ {y['name']} }} }} }}",
                                   x["name"], y["name"])
                        break
            elif k2 == "ENUM":
                sel = (f"regionsCondition {{ {f['name']} {{ {x['name']} }} }}",
                       x["name"], None)
            if sel:
                break
    if sel:
        break

if not sel:
    print("!! 未拼出查询，看上面结构人工定")
    sys.exit(1)

subquery, cfield, codef = sel
print("\n使用子查询:", subquery)
q = ("{ markets(first: 20) { nodes { id handle name enabled type "
     f"conditions {{ {subquery} }} }} }}")
mc = gql(q)
all_codes = set()
for m in mc["markets"]["nodes"]:
    rc = m["conditions"]["regionsCondition"]
    # 沿着已知结构取: {regions:{countries:[{code}]}} 形态不一，直接找
    def collect(node, out):
        if isinstance(node, dict):
            if codef and codef in node:
                out.append(node[codef])
            for v in node.values():
                collect(v, out)
        elif isinstance(node, list):
            for v in node:
                collect(v, out)
    codes = []
    collect(rc, codes)
    codes = sorted(set(codes))
    all_codes |= set(codes)
    print(f'\n[{m["name"]}] type={m.get("type")} enabled={m["enabled"]} '
          f'countries={len(codes)}: {",".join(codes)}')

print(f"\n市场覆盖国家总数: {len(all_codes)}")
bad = ("BR CH CL CO CY DK EE ES FI FR HU IE LT LU LV MD MT MY NL NO NZ "
       "PE PH PL PT RO RS SE SI SK UA").split()
missing = [c for c in bad if c not in all_codes]
print(f"31 失败国不在任何市场: {len(missing)} -> {missing}")
