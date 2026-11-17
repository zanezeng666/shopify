# -*- coding: utf-8 -*-
"""临时 SSH 执行通道（部署完删除）。
用法: $env:HK_PW='...'; uv run --with paramiko python scripts/_ssh.py "命令"
"""
import os
import sys

import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("101.32.33.21", username="root", password=os.environ["HK_PW"], timeout=20, look_for_keys=False, allow_agent=False)
_, stdout, stderr = c.exec_command(sys.argv[1], timeout=180)
out = stdout.read().decode(errors="replace")
err = stderr.read().decode(errors="replace")
if out:
    print(out)
if err.strip():
    print("[stderr]", err)
c.close()
