# -*- coding: utf-8 -*-
"""双 scope 重新授权（adwords + content）→ 新 refresh_token
用法: python oauth_content_flow.py [env文件路径]
流程: 打印/弹出授权 URL → 用户浏览器同意 → Google 回调 localhost:8745
      → 自动用 code 换 token → 结果写 %TEMP%\\oauth_result.json
"""
import http.server
import json
import os
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser

ENV = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.environ.get("TEMP", "."), "bmai_env.txt")
OUT = os.path.join(os.environ.get("TEMP", "."), "oauth_result.json")
REDIRECT = "http://localhost:8745/callback"
SCOPE = ("https://www.googleapis.com/auth/adwords "
         "https://www.googleapis.com/auth/content")

cred = {}
for line in open(ENV, encoding="utf-8", errors="ignore"):
    line = line.strip()
    if line.startswith("GOOGLE_CLIENT_ID="):
        cred["client_id"] = line.split("=", 1)[1]
    elif line.startswith("GOOGLE_CLIENT_SECRET="):
        cred["client_secret"] = line.split("=", 1)[1]
if not cred:
    print("FATAL: 未从", ENV, "解析到 GOOGLE_CLIENT_ID/SECRET")
    sys.exit(1)

auth_url = ("https://accounts.google.com/o/oauth2/v2/auth?"
            + urllib.parse.urlencode({
                "client_id": cred["client_id"],
                "redirect_uri": REDIRECT,
                "response_type": "code",
                "scope": SCOPE,
                "access_type": "offline",
                "prompt": "consent",
                "include_granted_scopes": "true"}))
print("AUTH_URL:", auth_url, flush=True)

result = {}


class CB(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in q:
            result["code"] = q["code"][0]
            result["scope"] = q.get("scope", [""])[0]
        body = ("授权成功，此页面可关闭。" if "code" in q
                else "等待授权参数…").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = http.server.HTTPServer(("127.0.0.1", 8745), CB)
threading.Thread(target=lambda: [srv.handle_request()
                                 for _ in iter(lambda: not result, True)],
                 daemon=True).start()
webbrowser.open(auth_url)

deadline = time.time() + 1800
while not result.get("code") and time.time() < deadline:
    time.sleep(2)
srv.shutdown()
if not result.get("code"):
    print("TIMEOUT: 30 分钟未收到回调。如浏览器显示无法访问 localhost，"
          "请把地址栏完整 URL 发给助手。")
    sys.exit(1)
print("code 已收到, granted scope:", result["scope"], flush=True)

data = urllib.parse.urlencode({
    "code": result["code"], "client_id": cred["client_id"],
    "client_secret": cred["client_secret"], "redirect_uri": REDIRECT,
    "grant_type": "authorization_code"}).encode()
tok = json.load(urllib.request.urlopen(urllib.request.Request(
    "https://oauth2.googleapis.com/token", data=data)))
print("token scope:", tok.get("scope"), flush=True)
print("REFRESH_TOKEN:", tok.get("refresh_token"), flush=True)
json.dump(tok, open(OUT, "w"))
print("已写入", OUT)
