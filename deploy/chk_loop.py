import subprocess
import time

PID = "3271274"
SPY = "/home/jason/shopify-admin/.venv/bin/py-spy"


def dump():
    r = subprocess.run([SPY, "dump", "--pid", PID], capture_output=True, text=True)
    keep = [ln for ln in r.stdout.splitlines()
            if any(k in ln for k in ("graphql", "service.py", "SSLSocket", "sleep", "run_pricing"))]
    return keep


def conns():
    r = subprocess.run(["ss", "-tnp"], capture_output=True, text=True)
    return [ln.strip() for ln in (r.stdout + r.stderr).splitlines() if PID in ln and ":443" in ln]


for i in range(3):
    print(f"--- t{i} {time.strftime('%H:%M:%S')} ---")
    for ln in dump():
        print(ln)
    print("conn:", conns())
    if i < 2:
        time.sleep(35)
