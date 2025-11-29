# Stem Splitter Web

简洁黑白风格的本地音轨提取网页：调用 Demucs 将歌曲分轨，并生成去人声的纯音乐版，内置波形和播放进度展示，适合作为个人工作流工具或 Demo。

> 本项目设计为在本地或你自己控制的服务器上运行，不适合直接部署到 Cloudflare Workers / Pages。

---

## 快速开始（本地）

在已安装 Python 3.10 和 ffmpeg 的 macOS / Linux 上：

```bash
git clone <你的仓库地址> stem-splitter
cd stem-splitter
bash scripts/run_local.sh
```

然后访问：

```text
http://127.0.0.1:5000/
```

首次运行会自动创建虚拟环境并安装 Demucs 等依赖，时间可能稍长。之后上传一首歌即可看到分轨进度与结果页面（包含各轨道波形 + 播放控件）。

---

## 更多信息

- 详细功能说明、部署建议、Demo 用法和安全提示，请查看：`docs/guide.md`

