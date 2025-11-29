#!/usr/bin/env bash
set -euo pipefail

# 一键本地启动脚本：
# - 创建 Python 虚拟环境（若不存在）
# - 安装 Flask 等依赖
# - 启动 Flask 应用

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "未找到 $PYTHON_BIN，请先安装 Python 3。"
  exit 1
fi

VENV_DIR="$BASE_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "未检测到虚拟环境，将使用 $PYTHON_BIN 创建："
  echo "  $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

echo "激活虚拟环境并安装依赖（如有需要）..."
source "$VENV_DIR/bin/activate"

pip install --upgrade pip >/dev/null 2>&1 || true
pip install -r requirements.txt

export FLASK_SECRET_KEY="${FLASK_SECRET_KEY:-please-change-me}"
export PORT="${PORT:-5000}"

echo
echo "启动应用："
echo "  URL: http://127.0.0.1:${PORT}/"
echo

python app.py

