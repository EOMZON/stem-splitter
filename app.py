import html
import json
import os
import re
import subprocess
import uuid
from pathlib import Path

from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    stream_with_context,
    url_for,
)


BASE_DIR = Path(__file__).resolve().parent

# 这里默认指向当前网站工程本身，
# 如需改为其它分轨工程，可在运行前设置环境变量 DEMUCS_PROJECT_ROOT
DEMUCS_PROJECT_ROOT = Path(
    os.environ.get(
        "DEMUCS_PROJECT_ROOT",
        str(BASE_DIR),
    )
).resolve()

DEMUCS_SCRIPT = DEMUCS_PROJECT_ROOT / "scripts" / "demucs_one.sh"
MIX_SCRIPT = DEMUCS_PROJECT_ROOT / "scripts" / "mix_instrumental_from_stems.sh"
STEMS_ROOT = DEMUCS_PROJECT_ROOT / "stems" / "htdemucs"

UPLOAD_ROOT = BASE_DIR / "uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def _slugify(name: str) -> str:
    """生成适合用作 slug 的安全字符串."""
    name = name.strip().lower()
    name = re.sub(r"[^\w\-]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")
    if not name:
        name = "track"
    # 避免和已有目录冲突，加一个短随机后缀
    short_id = uuid.uuid4().hex[:6]
    return f"{name}-{short_id}"


def run_demucs_and_mix(input_path: Path) -> str:
    """
    调用外部脚本：
    - demucs_one.sh 做分轨
    - mix_instrumental_from_stems.sh 合成不含人声的轻音乐

    返回 slug，前端通过 slug 构造下载地址。
    """
    if not DEMUCS_SCRIPT.is_file():
        raise RuntimeError(f"未找到 Demucs 脚本：{DEMUCS_SCRIPT}")

    if not MIX_SCRIPT.is_file():
        raise RuntimeError(f"未找到轻音乐合成脚本：{MIX_SCRIPT}")

    stem = input_path.stem
    slug = _slugify(stem)

    # 1. 调用 Demucs 分轨
    subprocess.run(
        ["bash", str(DEMUCS_SCRIPT), str(input_path), slug],
        cwd=str(DEMUCS_PROJECT_ROOT),
        check=True,
    )

    # 2. 基于分轨合成去人声轻音乐
    subprocess.run(
        ["bash", str(MIX_SCRIPT), slug],
        cwd=str(DEMUCS_PROJECT_ROOT),
        check=True,
    )

    return slug


def create_app() -> Flask:
    app = Flask(__name__)
    # 用于 flash 消息，生产环境请改成更安全的值
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

    # 限制上传大小（这里设为 200MB，可按需调整）
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

    @app.route("/", methods=["GET"])
    def index():
        # 收集已有分轨结果作为历史记录
        history_tracks: list[dict] = []
        if STEMS_ROOT.is_dir():
            try:
                # 按修改时间倒序排列，最近的在前
                stem_dirs = sorted(
                    [p for p in STEMS_ROOT.iterdir() if p.is_dir()],
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
            except OSError:
                stem_dirs = []

            for stem_dir in stem_dirs:
                slug = stem_dir.name

                # 至少存在一个音轨文件才算有效历史
                has_stem_file = any(
                    (stem_dir / f"{stem}.wav").is_file()
                    for stem in ["vocals", "drums", "bass", "other"]
                ) or (stem_dir / f"{slug}_instrumental.wav").is_file()
                if not has_stem_file:
                    continue

                # 展示名称：尝试去掉 slug 末尾的随机短 id
                display_title = slug
                m = re.search(r"-(?P<id>[0-9a-f]{6})$", slug)
                if m:
                    base = slug[: m.start()]
                    if base:
                        display_title = base.replace("-", " ")

                history_tracks.append(
                    {
                        "slug": slug,
                        "title": display_title,
                        "has_instrumental": (stem_dir / f"{slug}_instrumental.wav").is_file(),
                    }
                )

                # 只展示最近的若干条，避免列表过长
                if len(history_tracks) >= 20:
                    break

        return render_template("index.html", history_tracks=history_tracks)

    @app.route("/process", methods=["POST"])
    def process():
        file = request.files.get("audio")
        if not file or file.filename == "":
            flash("请先选择要上传的音频文件。")
            return redirect(url_for("index"))

        filename = file.filename
        # 允许任意格式，这里不做扩展名过滤
        safe_name = re.sub(r"[^\w.\-]+", "_", filename)
        upload_path = UPLOAD_ROOT / safe_name
        file.save(upload_path)

        try:
            slug = run_demucs_and_mix(upload_path)
        except subprocess.CalledProcessError:
            flash("分轨或合成过程中出现错误，请检查 Demucs 环境。")
            return redirect(url_for("index"))
        except Exception as exc:  # noqa: BLE001
            flash(str(exc))
            return redirect(url_for("index"))

        return redirect(url_for("track_detail", slug=slug))

    def _iter_cmd(cmd: list[str]) -> list[str]:
        proc = subprocess.Popen(
            cmd,
            cwd=str(DEMUCS_PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            yield line.rstrip("\n")
        proc.stdout.close()
        proc.wait()
        if proc.returncode:
            raise subprocess.CalledProcessError(proc.returncode, cmd)

    @app.route("/process_stream", methods=["POST"])
    def process_stream():
        file = request.files.get("audio")
        if not file or file.filename == "":
            flash("请先选择要上传的音频文件。")
            return redirect(url_for("index"))

        filename = file.filename
        safe_name = re.sub(r"[^\w.\-]+", "_", filename)
        upload_path = UPLOAD_ROOT / safe_name
        file.save(upload_path)

        stem = upload_path.stem
        slug = _slugify(stem)

        def generate():
            yield "<!doctype html><html><head><meta charset='utf-8'>"
            yield "<title>正在提取音轨...</title>"
            yield "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            yield "<style>body{background:#000;color:#f5f5f5;font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;padding:24px;}pre{white-space:pre-wrap;font-size:12px;line-height:1.4;background:#050505;border:1px solid #333;border-radius:8px;padding:12px;max-height:60vh;overflow:auto;}h1{font-size:18px;margin:0 0 8px;}p{margin:4px 0 12px;color:#aaa;} .status{margin-top:8px;font-size:12px;color:#888;}</style>"
            yield "<script>function addLog(line){var el=document.getElementById('log');if(!el)return;el.textContent+=line+'\\n';el.scrollTop=el.scrollHeight;}function setStatus(text){var s=document.getElementById('status');if(s)s.textContent=text;}</script>"
            yield "</head><body>"
            yield "<h1>正在提取音轨</h1>"
            yield "<p>这一步可能需要几分钟，下面是 Demucs 的进度输出：</p>"
            yield "<pre id='log'></pre>"
            yield "<div class='status' id='status'>准备开始...</div>"

            try:
                yield "<script>setStatus('Demucs 分轨进行中...');</script>"
                cmd1 = ["bash", str(DEMUCS_SCRIPT), str(upload_path), slug]
                for line in _iter_cmd(cmd1):
                    safe = html.escape(line)
                    chunk = json.dumps(safe)
                    yield f"<script>addLog({chunk});</script>"

                yield "<script>setStatus('正在合成去人声纯音乐...');</script>"
                cmd2 = ["bash", str(MIX_SCRIPT), slug]
                for line in _iter_cmd(cmd2):
                    safe = html.escape(line)
                    chunk = json.dumps(safe)
                    yield f"<script>addLog({chunk});</script>"

            except subprocess.CalledProcessError as exc:  # noqa: BLE001
                msg = f"命令失败：{' '.join(str(p) for p in exc.cmd)} (退出码 {exc.returncode})"
                chunk = json.dumps(msg)
                yield f"<script>addLog({chunk});setStatus('处理失败，请检查 Demucs 环境。');</script>"
                yield "</body></html>"
                return

            yield "<script>setStatus('完成，正在跳转到结果页...');</script>"
            target = url_for("track_detail", slug=slug)
            yield f"<script>window.location={json.dumps(target)};</script>"
            yield "</body></html>"

        return Response(stream_with_context(generate()), mimetype="text/html")

    @app.route("/track/<slug>", methods=["GET"])
    def track_detail(slug: str):
        stem_dir = STEMS_ROOT / slug
        stems = []
        for stem_name in ["vocals", "drums", "bass", "other"]:
            path = stem_dir / f"{stem_name}.wav"
            stems.append(
                {
                    "name": stem_name,
                    "exists": path.is_file(),
                    "download_url": url_for(
                        "download_stem", slug=slug, stem=stem_name
                    ),
                    "audio_url": url_for("audio_stem", slug=slug, stem=stem_name),
                }
            )

        instrumental_path = stem_dir / f"{slug}_instrumental.wav"

        return render_template(
            "track.html",
            slug=slug,
            stem_dir=stem_dir,
            stems=stems,
            instrumental_exists=instrumental_path.is_file(),
            instrumental_url=url_for("download_stem", slug=slug, stem="instrumental"),
            instrumental_stream_url=url_for(
                "audio_stem", slug=slug, stem="instrumental"
            ),
        )

    @app.route("/download/<slug>/<stem>", methods=["GET"])
    def download_stem(slug: str, stem: str):
        stem_dir = STEMS_ROOT / slug

        if stem in {"vocals", "drums", "bass", "other"}:
            file_path = stem_dir / f"{stem}.wav"
        elif stem == "instrumental":
            file_path = stem_dir / f"{slug}_instrumental.wav"
        else:
            flash("不支持的音轨类型。")
            return redirect(url_for("track_detail", slug=slug))

        if not file_path.is_file():
            flash("找不到对应的音轨文件，请确认分轨是否成功。")
            return redirect(url_for("track_detail", slug=slug))

        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_path.name,
        )

    @app.route("/audio/<slug>/<stem>", methods=["GET"])
    def audio_stem(slug: str, stem: str):
        stem_dir = STEMS_ROOT / slug

        if stem in {"vocals", "drums", "bass", "other"}:
            preview_path = stem_dir / f"{stem}_preview.mp3"
            if preview_path.is_file():
                file_path = preview_path
            else:
                file_path = stem_dir / f"{stem}.wav"
        elif stem == "instrumental":
            preview_path = stem_dir / f"{slug}_instrumental_preview.mp3"
            if preview_path.is_file():
                file_path = preview_path
            else:
                file_path = stem_dir / f"{slug}_instrumental.wav"
        else:
            flash("不支持的音轨类型。")
            return redirect(url_for("track_detail", slug=slug))

        if not file_path.is_file():
            flash("找不到对应的音轨文件，请确认分轨是否成功。")
            return redirect(url_for("track_detail", slug=slug))

        return send_file(
            file_path,
            as_attachment=False,
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
