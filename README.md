# Stem Splitter Web

一个简洁的黑白风格网页，用于在本地运行 Demucs 对歌曲进行分轨，并生成去人声的纯音乐版本。  
前端内置波形 + 播放进度显示，适合作为个人工作流工具或 Demo 展示。

> ⚠️ 本项目设计为 **本地 / 自己控制的服务器** 上运行。  
> 由于依赖 Demucs + PyTorch + ffmpeg 等重量级组件，不适合直接部署到 Cloudflare Workers / Pages 这类无服务器环境。

---

## 功能简介

- 上传任意常见格式的音频文件（MP3 / WAV / FLAC / M4A 等）
- 使用 Demucs 自动分轨，输出：
  - `vocals.wav`
  - `drums.wav`
  - `bass.wav`
  - `other.wav`
- 通过脚本自动合成去人声的纯音乐：`<slug>_instrumental.wav`
- 为所有音轨生成压缩预览音频（`*_preview.mp3`），用于网页端快速加载与波形展示
- 结果页中：
  - 每条音轨都有独立的波形图
  - 带“播放/暂停 + 图标 + 时间（已播 / 剩余）”的控制条
  - 支持下载完整 WAV 文件
- 分轨进度页面：
  - 实时显示 Demucs 的命令行输出（含进度条类似 `0%|...`）
  - 完成后自动跳转到结果页

---

## 目录结构

- `app.py`  
  Flask 应用入口，负责：
  - 上传文件处理
  - 调用 shell 脚本执行 Demucs 分轨与纯音乐合成
  - 结果页展示、音轨下载与在线播放
- `scripts/demucs_one.sh`  
  单首歌曲分轨脚本，自动：
  - 创建本项目下的虚拟环境 `spleeter-py310/`
  - 安装 `demucs` 与相关依赖
  - 调用 Demucs 输出分轨
  - 为每条分轨生成 `*_preview.mp3`
- `scripts/mix_instrumental_from_stems.sh`  
  基于 Demucs 分轨结果合成去人声纯音乐，并生成 `<slug>_instrumental_preview.mp3`。
- `templates/index.html`  
  上传页（黑白极简风格）。
- `templates/track.html`  
  分轨结果页，含波形和播放控制。
- `static/style.css`  
  全站样式。
- `tests/playwright_smoke.py`  
  一个极简的 Playwright 端到端示例（可选使用）。

运行时生成的目录（**不会进入 git 仓库，见 `.gitignore`**）：

- `spleeter-py310/`：Demucs 专用虚拟环境（由脚本自动创建）
- `stems/`：分轨结果与纯音乐输出（含 `*_preview.mp3`）
- `uploads/`：上传的原始音频

---

## 推荐机器配置

本项目依赖 Demucs + PyTorch，属于 CPU / 内存相对较重的任务。  
如果希望在服务器上跑 Demo，建议最低配置：

- **2 vCPU**
- **2 GiB RAM**
- **40 GiB 磁盘**（ESSD / SSD 均可）

注意：

- 本地 macOS / Linux 桌面机器通常也可以顺利运行，只要有可用的 Python 3.10 和 ffmpeg。
- 若并发用户较多或歌曲较长，建议提升内存与 CPU。

---

## 本地运行（macOS / Linux）

### 1. 克隆仓库

```bash
git clone <你的仓库地址> stem-splitter
cd stem-splitter
```

### 2. 安装 Flask（网页部分）

建议使用虚拟环境：

```bash
python3 -m venv venv
source venv/bin/activate  # Windows 请使用 venv\Scripts\activate

pip install -r requirements.txt
```

> Demucs 及其依赖 **无需手动安装**，由 `scripts/demucs_one.sh` 在第一次分轨时自动安装到 `spleeter-py310/`。

### 3. 确保系统已安装 ffmpeg

例如：

- macOS（Homebrew）：
  ```bash
  brew install ffmpeg
  ```
- Ubuntu / Debian：
  ```bash
  sudo apt update
  sudo apt install -y ffmpeg
  ```

### 4. 启动服务

设置一个随机的 Secret Key（线上环境务必修改）：

```bash
export FLASK_SECRET_KEY="please-change-me"
export PORT=5000  # 可选：修改为任意可用端口
python app.py
```

浏览器访问：

```text
http://127.0.0.1:5000/
```

- 上传一首歌后，会进入“正在提取音轨”页，实时显示 Demucs 的命令行进度。
- 处理完成后自动跳转到结果页，展示各个分轨与去人声纯音乐的波形与下载按钮。

---

## 部署建议（Linux 服务器 + Cloudflare）

如果你有一台 Linux 服务器（例如配置：2 vCPU / 2 GiB / 40 GiB），可以：

1. 按“本地运行”的步骤在服务器上安装 Python / ffmpeg，并部署本项目。  
2. 使用 `gunicorn` 等进程管理工具提升稳定性（可选）：
   ```bash
   pip install gunicorn
   gunicorn -w 1 -b 0.0.0.0:5000 app:create_app
   ```
3. 使用 Cloudflare：
   - 只用作 **域名与 HTTPS / 反向代理**；
   - 真正的 Demucs 分轨仍在你的服务器上执行；
   - 可以选择：
     - 直接在 DNS 中把二级域名指向服务器 IP；
     - 或使用 Cloudflare Tunnel 把 `https://xxx.yourdomain.com` 暴露到服务器的 `http://localhost:5000`。

> 由于 Demucs 依赖较大、执行时间较长，不建议尝试将本项目直接运行在 Cloudflare Workers / Pages Functions 内部。

---

## Demo 用法建议

本仓库 **不包含任何真实音频文件**。如需展示 Demo：

1. 自己准备一首有版权许可的音频，并在本地运行一次分轨：  
   - 通过网页上传即可；
   - 或手动用脚本运行：
     ```bash
     bash scripts/demucs_one.sh "path/to/your_song.mp3" my-demo
     bash scripts/mix_instrumental_from_stems.sh my-demo
     ```
2. 分轨和预览文件会出现在：
   ```text
   stems/htdemucs/my-demo/
   ```
3. 在浏览器访问 `/track/my-demo` 即可查看 Demo 界面。

如果你希望制作只读 Demo（不给用户上传权限）：

- 可以在 `templates/index.html` 中隐藏或禁用上传表单，仅在 README 或导航中给出若干固定 slug 的链接，例如 `/track/my-demo-1`、`/track/my-demo-2`。

---

## 界面截图（示例占位）

建议在本地运行后自行截图，并将图片放入仓库，例如：

- `docs/screenshots/home.png`：上传首页
- `docs/screenshots/progress.png`：分轨进度页
- `docs/screenshots/result.png`：分轨结果页（含波形与播放按钮）

在 README 中引用（示例）：

```markdown
![上传首页](docs/screenshots/home.png)
![分轨进度](docs/screenshots/progress.png)
![分轨结果](docs/screenshots/result.png)
```

---

## 测试（可选）

仓库包含一个极简的 Playwright 脚本，用于检查首页是否能正常打开：

```bash
python -m pip install playwright
playwright install chromium

export APP_URL="http://127.0.0.1:5000/"
python tests/playwright_smoke.py
```

这一步完全可选，仅用于开发者自测。

---

## 安全与隐私提示

- 所有上传文件与分轨结果默认保存在本地的 `uploads/` 与 `stems/` 目录中，**不会自动上传到任何第三方服务**。
- 请勿将包含个人或受版权保护的音频文件提交到公开仓库。`.gitignore` 已默认忽略这些目录。
- 线上部署时，请务必通过环境变量覆盖 `FLASK_SECRET_KEY`，不要使用示例值。

