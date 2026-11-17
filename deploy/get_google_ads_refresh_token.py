"""Google Ads OAuth2 refresh token 一次性生成器。

前置条件：
  1. Google Cloud Console 已创建 OAuth 客户端（Web 应用），已获授权的重定向 URI 已添加
     http://localhost:8080/oauth2callback
  2. OAuth 同意屏幕已发布为「正式版」（测试版 refresh_token 7 天过期）。

用法（本地 Windows python 直接跑，零第三方依赖）：
  python deploy/get_google_ads_refresh_token.py --client-id=xxx --client-secret=yyy
  可选 --email=your@gmail.com 指定登录账号

流程：自动开浏览器 -> 登录拥有 Google Ads 账户的 Google 账号 -> 授权
      -> 回调 localhost:8080 -> 终端打印 .env 四件套。
"""

import argparse
import http.server
import json
import threading
import time
import urllib.parse
import urllib.request
import webbrowser

PORT = 8080
REDIRECT_PATH = "/oauth2callback"
REDIRECT_URI = f"http://localhost:{PORT}{REDIRECT_PATH}"
SCOPE = "https://www.googleapis.com/auth/adwords"
AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--client-id", required=True)
    ap.add_argument("--client-secret", required=True)
    ap.add_argument("--email", default="", help="可选：登录账号 hint")
    args = ap.parse_args()

    done = threading.Event()
    result: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != REDIRECT_PATH:
                self.send_response(404)
                self.end_headers()
                return
            qs = urllib.parse.parse_qs(parsed.query)
            result["code"] = qs.get("code", [None])[0]
            result["error"] = qs.get("error", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<h2>授权成功，请回到终端查看 refresh_token。</h2>".encode("utf-8")
            )
            done.set()

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("localhost", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    params = {
        "client_id": args.client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",  # 必须：否则不发 refresh_token
        "prompt": "consent",       # 重复授权时也强制重发 refresh_token
    }
    if args.email:
        params["login_hint"] = args.email
    url = AUTH_URI + "?" + urllib.parse.urlencode(params)
    print("若浏览器未自动打开，请手动复制以下网址到浏览器访问：\n")
    print(url + "\n")
    webbrowser.open(url)

    while not done.wait(timeout=0.2):
        pass
    server.shutdown()

    if result.get("error"):
        raise SystemExit(f"授权被拒绝: {result['error']}")

    data = urllib.parse.urlencode(
        {
            "code": result["code"],
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    req = urllib.request.Request(TOKEN_URI, data=data)
    with urllib.request.urlopen(req) as resp:
        tok = json.loads(resp.read())

    print("\n=== 成功！把以下值写入 .env ===")
    print(f"GOOGLE_ADS_CLIENT_ID={args.client_id}")
    print(f"GOOGLE_ADS_CLIENT_SECRET={args.client_secret}")
    print(f"GOOGLE_ADS_REFRESH_TOKEN={tok.get('refresh_token')}")
    print("GOOGLE_ADS_DEVELOPER_TOKEN=<你的 Google Ads 开发者令牌>")
    if not tok.get("refresh_token"):
        print(
            "\n警告: 本次未返回 refresh_token。请到 "
            "https://myaccount.google.com/permissions 撤销本应用授权后重跑本脚本。"
        )


if __name__ == "__main__":
    main()
