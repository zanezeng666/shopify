#!/bin/bash
# 探测视频合成环境
echo "--- ffmpeg ---"
which ffmpeg && ffmpeg -version 2>/dev/null | head -1 || echo "无系统 ffmpeg"
echo "--- 字体 ---"
ls /usr/share/fonts/ 2>/dev/null
find /usr/share/fonts -name "*.ttf" 2>/dev/null | head -8
echo "--- python 库 ---"
cd /home/jason/shopify-admin
sudo -u jason env HOME=/home/jason .venv/bin/python - <<'EOF'
mods = ["PIL", "numpy", "httpx", "imageio", "imageio_ffmpeg", "cv2"]
for m in mods:
    try:
        mod = __import__(m)
        print(f"{m}: {getattr(mod, '__version__', 'ok')}")
    except ImportError:
        print(f"{m}: 无")
EOF
