#!/usr/bin/env bash
set -euo pipefail

# 使用 Demucs 对单首歌曲进行分轨（本项目本地版）
# 用法：
#   1) 默认处理 samples/xindideyu.mp3（如存在）：
#        bash scripts/demucs_one.sh
#   2) 指定输入文件和 slug（用于命名输出目录）：
#        bash scripts/demucs_one.sh "path/to/your_song.mp3" your_slug

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 首选 Python 3.10（兼容性更好），若没有则退回 python3
PYTHON_BIN="${PYTHON_BIN:-python3.10}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "未找到 python3.10 或 python3，请先安装 Python 3。"
    exit 1
  fi
fi

# 为 Demucs 准备的虚拟环境目录（自动创建，位于当前网站工程下）
VENV_DIR="$BASE_DIR/spleeter-py310"

if [ ! -d "$VENV_DIR" ]; then
  echo "未检测到虚拟环境，将使用 $PYTHON_BIN 创建："
  echo "  $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

PYTHON_VENV="$VENV_DIR/bin/python"
DEM_UCS_BIN="$VENV_DIR/bin/demucs"

# 如未安装 demucs，则自动安装（首次运行会稍久）
if [ ! -x "$DEM_UCS_BIN" ]; then
  echo "虚拟环境中未检测到 demucs，正在安装（仅首次运行需要）："
  "$PYTHON_VENV" -m pip install --upgrade pip
  "$PYTHON_VENV" -m pip install demucs
fi

# 确保安装 torchcodec（新版本 torchaudio 保存音频时需要）
if ! "$PYTHON_VENV" -c "import torchcodec" >/dev/null 2>&1; then
  echo "虚拟环境中未检测到 torchcodec，正在安装："
  "$PYTHON_VENV" -m pip install torchcodec
fi

INPUT="${1:-"$BASE_DIR/samples/xindideyu.mp3"}"
SLUG="${2:-xindideyu}"
OUT_BASE="$BASE_DIR/stems"

if [ ! -f "$INPUT" ]; then
  echo "找不到输入文件：$INPUT"
  echo "请确认路径是否正确，或显式传入路径，例如："
  echo "  bash scripts/demucs_one.sh \"path/to/your_song.mp3\" your_slug"
  exit 1
fi

mkdir -p "$OUT_BASE"

echo "开始使用 Demucs 分轨："
echo "  输入：$INPUT"
echo "  slug：$SLUG"
echo "  输出父目录：$OUT_BASE"
echo

# 限制 CPU 线程数（可通过环境变量覆盖，默认 1）
CPU_THREADS="${CPU_THREADS:-1}"
export OMP_NUM_THREADS="$CPU_THREADS"
export MKL_NUM_THREADS="$CPU_THREADS"
export NUMEXPR_NUM_THREADS="$CPU_THREADS"
export OPENBLAS_NUM_THREADS="$CPU_THREADS"
export VECLIB_MAXIMUM_THREADS="$CPU_THREADS"

echo "  CPU 线程上限：$CPU_THREADS"

# Demucs 默认会在 -o 指定目录下再创建一个以模型名命名的子目录（如 htdemucs）
# 这里通过 --filename 把轨道统一收敛到 htdemucs/<slug>/ 下，便于查找。
"$DEM_UCS_BIN" \
  -o "$OUT_BASE" \
  --filename "$SLUG/{stem}.{ext}" \
  "$INPUT"

# 为每条分轨生成压缩预览音频（mp3），用于前端波形展示与试听
STEM_DIR="$OUT_BASE/htdemucs/$SLUG"
if [ -d "$STEM_DIR" ]; then
  echo
  echo "开始为各个分轨生成预览音频（mp3，用于网页播放）："
  for stem in vocals drums bass other; do
    WAV="$STEM_DIR/$stem.wav"
    PREVIEW="$STEM_DIR/${stem}_preview.mp3"
    if [ -f "$WAV" ]; then
      if [ -f "$PREVIEW" ]; then
        echo "  跳过 $stem（预览已存在）：$PREVIEW"
      else
        echo "  生成 $stem 预览：$PREVIEW"
        ffmpeg -y -loglevel error \
          -i "$WAV" \
          -ac 1 \
          -b:a 128k \
          "$PREVIEW" || echo "    生成预览失败：$PREVIEW" >&2
      fi
    fi
  done
fi

echo
echo "分轨完成。你可以在以下目录查看结果："
echo "  $OUT_BASE/htdemucs/$SLUG/"
