# -*- coding: utf-8 -*-
"""Merchant Center(content scope) OAuth2 refresh token 一次性生成器。

复用 get_google_ads_refresh_token.py 的 OAuth 客户端与回调流程，
仅 scope 换成 https://www.googleapis.com/auth/content
（Content API v2.1 + merchantapi 共用该 scope）。

用法（本地 Windows，零第三方依赖）：
  python deploy/get_mc_refresh_token.py --cred-file <两行文件: ID/SECRET>
流程：自动开浏览器 -> 登录拥有 MC 账户权限的 Google 账号 -> 授权
      -> 回调 localhost:8080 -> 终端打印 GOOGLE_MC_REFRESH_TOKEN。
"""
import argparse
import http.server
import json
import threading
import urllib.parse
import urllib.request
import webbrowser

PORT = 8080
REDIRECT_PATH = "/oauth2callback"
REDIRECT_URI = f"http://localhost:{PORT}{REDIRECT_PATH}"
SCOPE = "https://www.googleapis.com/auth/content"
AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
TIMEOUT_S = 600


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cred-file", required=True,
                    help="两行文本：第一行 client_id，第二行 client_secret")
    args = ap.parse_args()

    with open(args.cred_file, encoding="utf-8") as f:
        cid_line, secret_line = [ln.strip() for ln in f.readlines()[:2]
                                 if ln.strip()][:2]
    # 兼容 "KEY=value" 或裸值两种格式
    client_id = cid_line.split("=", 1)[-1]
    client_secret = secret_line.split("=", 1)[-1]

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
                "<h2>MC 授权成功，请回到终端查看 refresh_token。</h2>".encode()
            )
            done.set()

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("localhost", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = AUTH_URI + "?" + urllib.parse.urlencode(params)
    print("若浏览器未自动打开，请手动复制以下网址到浏览器访问"
          f"（{TIMEOUT_S}s 内完成授权）：\n")
    print(url + "\n")
    try:
        webbrowser.open(url)
    except Exception:  # noqa
        pass

    if not done.wait(timeout=TIMEOUT_S):
        server.shutdown()
        raise SystemExit(f"等待授权超时({TIMEOUT_S}s)，请重跑。")
    server.shutdown()

    if result.get("error"):
        raise SystemExit(f"授权被拒绝: {result['error']}")

    data = urllib.parse.urlencode(
        {
            "code": result["code"],
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    req = urllib.request.Request(TOKEN_URI, data=data)
    with urllib.request.urlopen(req) as resp:
        tok = json.loads(resp.read())

    print("\n=== 成功！把以下值追加到服务器 .env ===")
    print(f"GOOGLE_MC_REFRESH_TOKEN={tok.get('refresh_token')}")
    print(f"授权 scope: {tok.get('scope')}")
    if tok.get("refresh_token"):
        import os
        import tempfile
        p = os.path.join(tempfile.gettempdir(), "mc_token.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write(f"GOOGLE_MC_REFRESH_TOKEN={tok['refresh_token']}\n")
        print(f"(已备份到 {p})")
    else:
        print("\n警告: 未返回 refresh_token。请到 "
              "https://myaccount.google.com/permissions 撤销本应用授权后重跑。")


if __name__ == "__main__":
    main()
