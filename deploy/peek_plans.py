# -*- coding: utf-8 -*-
import json

p = json.load(open("/tmp/allcat_plans.json"))
x = p[0]
print("keys:", list(x))
print("campaign:", x["campaign"])
print("path1:", x.get("path1"), "| url:", x.get("url"))
print("headlines(", len(x.get("headlines", [])), "):",
      x.get("headlines", [])[:6])
print("descriptions(", len(x.get("descriptions", [])), "):",
      x.get("descriptions", [])[:2])
for g in x.get("ad_groups", []):
    print("group:", g["name"], "| kw:", len(g["keywords"]),
          [k[1][:28] for k in g["keywords"][:4]])
print("total plans:", len(p))
