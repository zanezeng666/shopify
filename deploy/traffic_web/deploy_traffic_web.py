# -*- coding: utf-8 -*-
"""流量看板一键部署：依赖+key+systemd+nginx(traffic.bornmieo.com)+冒烟。幂等可重跑。root 执行。"""
import re
import secrets
import subprocess
import sys
import time

VENV = "/home/jason/shopify-admin/.venv"
ENVF = "/home/jason/shopify-admin/.env"
DIR = "/home/jason/traffic-web"
UNIT = "/etc/systemd/system/traffic-web.service"
NGINX = "/usr/local/nginx-1.30.2/conf/nginx.conf"


def run(cmd, **kw):
    print(f"$ {cmd[:110]}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stdout[-500:] if r.stdout else "", r.stderr[-500:] if r.stderr else "")
    return r


# ① 依赖
r = run(f"{VENV}/bin/pip show fastapi uvicorn | grep -c Name")
if (r.stdout or "").strip() != "2":
    run(f"{VENV}/bin/pip install -q fastapi 'uvicorn[standard]'")

# ② TRAFFIC_KEY
env = open(ENVF, encoding="utf-8").read()
m = re.search(r"^TRAFFIC_KEY=(\S+)$", env, re.M)
if m:
    key = m.group(1)
    print(f"key 已存在: {key[:4]}***")
else:
    key = secrets.token_urlsafe(12)
    with open(ENVF, "a", encoding="utf-8") as f:
        f.write(f"\nTRAFFIC_KEY={key}\n")
    run(f"chown jason:jason {ENVF} && chmod 600 {ENVF}")
    print(f"key 已生成: {key}")

# ③ systemd unit
unit = f"""[Unit]
Description=Traffic Quality Dashboard (GA4)
After=network.target

[Service]
Type=simple
User=jason
Group=jason
WorkingDirectory={DIR}
Environment=PYTHONUNBUFFERED=1
ExecStart={VENV}/bin/uvicorn app:app --host 127.0.0.1 --port 8010 --workers 1
Restart=always
RestartSec=3
StandardOutput=append:/var/log/traffic-web.log
StandardError=append:/var/log/traffic-web.log

[Install]
WantedBy=multi-user.target
"""
open(UNIT, "w").write(unit)
run("systemctl daemon-reload && systemctl enable --now traffic-web.service")
run("systemctl restart traffic-web.service")
time.sleep(4)
r = run("systemctl is-active traffic-web.service")
if "active" not in (r.stdout or ""):
    print(run("tail -12 /var/log/traffic-web.log").stdout)
    sys.exit("服务未起来，中止")

# ④ nginx server 块（幂等）
conf = open(NGINX, encoding="utf-8").read()
if "traffic.bornmieo.com" in conf:
    print("nginx 块已存在，跳过")
else:
    block = """    server {
        listen 443 ssl;
        server_name traffic.bornmieo.com;

        ssl_certificate     /etc/nginx/ssl/nginx.crt;
        ssl_certificate_key /etc/nginx/ssl/nginx.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_session_timeout 5m;

        location / {
            proxy_pass http://127.0.0.1:8010;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Connection "";
            proxy_read_timeout 120s;
        }
    }
    server {
        listen 80;
        server_name traffic.bornmieo.com;
        return 308 https://$host$request_uri;
    }
"""
    run(f"cp {NGINX} {NGINX}.bak_traffic")
    conf = conf.replace("    server {", block + "    server {", 1)
    open(NGINX, "w", encoding="utf-8").write(conf)
    t = run("/usr/local/nginx-1.30.2/sbin/nginx -t")
    if t.returncode != 0:
        run(f"cp {NGINX}.bak_traffic {NGINX}")
        sys.exit("nginx -t 失败已回滚：" + (t.stderr or "")[-300:])
    run("/usr/local/nginx-1.30.2/sbin/nginx -s reload")

# ⑤ 冒烟
r = run(f"curl -s 'http://127.0.0.1:8010/api/day?date=today&k={key}' | head -c 200")
print("本机 API:", (r.stdout or "")[:200])
time.sleep(1)
r = run(f"curl -sk -o /dev/null -w '%{{http_code}}' 'https://traffic.bornmieo.com/?k={key}'")
print("HTTPS 页面:", r.stdout)
r = run(f"curl -s -o /dev/null -w '%{{http_code}}' 'https://traffic.bornmieo.com/'")
print("无 key（应 401）:", r.stdout)
print(f"\n=== 访问地址: https://traffic.bornmieo.com/?k={key} ===")
