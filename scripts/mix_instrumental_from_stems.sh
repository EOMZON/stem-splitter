#!/usr/bin/env bash
set -euo pipefail

# 从 Demucs 分轨结果中合并「非人声部分」成一轨轻音乐（WAV）（本项目本地版）
# 用法：
#   1) 默认以示例 slug（rain-in-my-heart）为例：
#        bash scripts/mix_instrumental_from_stems.sh
#   2) 指定 slug（即 demucs_one.sh 使用的 slug）：
#        bash scripts/mix_instrumental_from_stems.sh my-song-slug
#   3) 指定 slug 与输出文件路径：
#        bash scripts/mix_instrumental_from_stems.sh my-song-slug "stems/htdemucs/my-song-slug/my-song-slug_instrumental.wav"
#
# 约定：
# - 分轨结果在：stems/htdemucs/<slug>/ 下，包含：
#     - vocals.wav
#     - drums.wav
#     - bass.wav
#     - other.wav
# - 本脚本会读取 drums/bass/other 三轨，适度降低鼓组音量，混合成一轨 WAV。

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEMS_MODEL_DIR="${STEMS_MODEL_DIR:-htdemucs}"  # 预留：如未来改模型目录名，可通过环境变量覆盖

SLUG="${1:-rain-in-my-heart}"
IN_DIR="$BASE_DIR/stems/$STEMS_MODEL_DIR/$SLUG"

if [ ! -d "$IN_DIR" ]; then
  echo "找不到分轨目录：$IN_DIR"
  echo "请先执行（示例）："
  echo "  cd \"$BASE_DIR\""
  echo "  bash scripts/demucs_one.sh \"path/to/your_song.mp3\" my-song-slug"
  echo "然后再运行本脚本："
  echo "  bash scripts/mix_instrumental_from_stems.sh my-song-slug"
  exit 1
fi

DRUMS="$IN_DIR/drums.wav"
BASS="$IN_DIR/bass.wav"
OTHER="$IN_DIR/other.wav"

for f in "$DRUMS" "$BASS" "$OTHER"; do
  if [ ! -f "$f" ]; then
    echo "缺少必要的分轨文件：$f"
    echo "请确认 Demucs 已成功输出 drums/bass/other 三轨。"
    exit 1
  fi
done

# 输出文件，默认放在同目录下，命名为 <slug>_instrumental.wav
OUT_FILE="${2:-"$IN_DIR/${SLUG}_instrumental.wav"}"

echo "开始合成轻音乐（不含人声）："
echo "  输入目录：$IN_DIR"
echo "  输出文件：$OUT_FILE"
echo

# 使用 ffmpeg 合并 drums/bass/other：
# - 适度降低鼓组音量（0.8），保留一些律动但不过于抢占空间；
# - bass 稍微降低（0.9），避免过重；
# - other 保持原始音量。
ffmpeg -y -loglevel error \
  -i "$DRUMS" \
  -i "$BASS" \
  -i "$OTHER" \
  -filter_complex "\
[0:a]volume=0.8[d]; \
[1:a]volume=0.9[b]; \
[2:a]volume=1.0[o]; \
[d][b][o]amix=inputs=3:normalize=0[aout]" \
  -map "[aout]" \
  -c:a pcm_s16le \
  "$OUT_FILE"

echo
echo "合成完成："
echo "  轻音乐（不含人声）已输出为：$OUT_FILE"

# 为纯音乐生成压缩预览音频（mp3），用于网页播放
PREVIEW="${OUT_FILE%.wav}_preview.mp3"
echo
echo "开始生成纯音乐预览音频（mp3，用于网页播放）："
echo "  预览文件：$PREVIEW"
ffmpeg -y -loglevel error \
  -i "$OUT_FILE" \
  -ac 1 \
  -b:a 128k \
  "$PREVIEW" || echo "  生成纯音乐预览失败：$PREVIEW" >&2
