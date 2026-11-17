#!/bin/bash
set -e
U=$(which uv || ls /root/.local/bin/uv 2>/dev/null || ls /home/jason/.local/bin/uv 2>/dev/null || true)
if [ -z "$U" ]; then echo "无 uv，尝试 curl 安装"; curl -LsSf https://astral.sh/uv/install.sh | sh; U=/root/.local/bin/uv; fi
echo "uv = $U"
$U pip install -q imageio-ffmpeg --python /home/jason/shopify-admin/.venv/bin/python -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 | tail -2
sudo -u jason env HOME=/home/jason /home/jason/shopify-admin/.venv/bin/python -c 'import imageio_ffmpeg; print("FFMPEG_EXE:", imageio_ffmpeg.get_ffmpeg_exe())'
