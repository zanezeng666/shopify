"""自省 marketUpdate 输入链: MarketUpdateInput -> conditions -> regions。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)


def leaf(t):
    while t.get("ofType"):
        t = t["ofType"]
    return t.get("kind"), t.get("name")


r2 = client.graphql(
    '{ __type(name: "Mutation") { fields { name args { name type '
    '{ kind name ofType { kind name ofType { kind name } } } } } } }')
targets = {}
for f in r2["__type"]["fields"]:
    if f["name"] in ("marketUpdate", "marketDelete"):
        print(f"{f['name']} args: " + ", ".join(
            f"{a['name']}:{leaf(a['type'])}" for a in f["args"]))
        for a in f["args"]:
            _, tn = leaf(a["type"])
            if tn and "Input" in tn:
                targets[tn] = True

seen = set()


def dump_input(tn, indent="  "):
    if tn in seen:
        print(f"{indent}{tn}: (已展示)")
        return
    seen.add(tn)
    it = client.graphql(
        '{ __type(name: "%s") { inputFields { name type '
        '{ kind name ofType { kind name ofType { kind name } } } } } }' % tn)
    if not it.get("__type"):
        print(f"{indent}{tn}: 不存在")
        return
    for x in it["__type"]["inputFields"]:
        k, t = leaf(x["type"])
        print(f"{indent}{x['name']}: {k} {t}")
        if k == "INPUT_OBJECT" and t:
            dump_input(t, indent + "  ")


for tn in targets:
    print(f"\n== {tn} ==")
    dump_input(tn)
