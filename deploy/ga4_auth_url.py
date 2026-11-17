# -*- coding: utf-8 -*-
"""生成 GA4 只读授权 URL（用户浏览器打开→同意→复制地址栏 code 发回）。"""
import os
import urllib.parse

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

params = {
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "redirect_uri": os.environ["GOOGLE_REDIRECT_URI"],
    "response_type": "code",
    "scope": "https://www.googleapis.com/auth/analytics.readonly",
    "access_type": "offline",   # 必须，才发 refresh_token
    "prompt": "consent",        # 强制重新发码
}
print("https://accounts.google.com/o/oauth2/v2/auth?"
      + urllib.parse.urlencode(params))
