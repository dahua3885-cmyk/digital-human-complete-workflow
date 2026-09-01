#!/usr/bin/env python3
"""Render the fixed portrait packaging, covers, QA report, and manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def default_config() -> Path:
    explicit = os.getenv("DIGITAL_HUMAN_PACKAGING_RUNTIME")
    if explicit:
        return Path(explicit).expanduser().resolve()
    codex_home = Path(os.getenv("CODEX_HOME", Path.home() / ".codex"))
    return codex_home / "runtimes" / "digital-human-packaging-fixed" / "runtime.json"


def hidden_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=hidden_flags())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def worker(args: argparse.Namespace) -> int:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    config = json.loads(args.config.read_text(encoding="utf-8"))
    ffmpeg = str(config["ffmpeg"])
    ffprobe = str(config["ffprobe"])
    font_path = str(config["font"])

    def font(size: int):
        return ImageFont.truetype(font_path, size=size)

    def wrapped(draw: ImageDraw.ImageDraw, text: str, current_font, max_width: int) -> list[str]:
        lines: list[str] = []
        current = ""
        for char in str(text).strip():
            candidate = current + char
            if current and draw.textbbox((0, 0), candidate, font=current_font)[2] > max_width:
                lines.append(current)
                current = char
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines

    probe = run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(args.source)])
    if probe.returncode != 0:
        raise RuntimeError("来源视频无法读取")
    media = json.loads(probe.stdout)
    duration = float(media.get("format", {}).get("duration", 0))
    streams = media.get("streams", [])
    if duration <= 0 or not any(item.get("codec_type") == "video" for item in streams):
        raise RuntimeError("来源视频没有有效画面或时长")
    if not any(item.get("codec_type") == "audio" for item in streams):
        raise RuntimeError("来源视频没有音轨，不能作为数字人口播包装输入")
    cards = json.loads(args.cards.read_text(encoding="utf-8"))
    captions = json.loads(args.captions.read_text(encoding="utf-8"))
    if not isinstance(cards, list) or not isinstance(captions, list):
        raise RuntimeError("信息卡或字幕时间线必须是 JSON 列表")
    for label, entries in (("信息卡", cards), ("字幕", captions)):
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise RuntimeError(f"{label}第 {index + 1} 项格式不正确")
            start = float(entry.get("start", -1))
            end = float(entry.get("end", -1))
            if start < 0 or end <= start or end > duration + 0.1:
                raise RuntimeError(f"{label}第 {index + 1} 项时间超出视频范围")
    out = args.output_dir
    work = out / "project"
    assets = work / "assets"
    covers = out / "covers"
    assets.mkdir(parents=True, exist_ok=True)
    covers.mkdir(parents=True, exist_ok=True)

    bg = Image.new("RGB", (1080, 1920), "#020711")
    draw = ImageDraw.Draw(bg)
    for x in range(0, 1080, 56):
        draw.line((x, 0, x, 1920), fill="#071727", width=1)
    for y in range(0, 1920, 56):
        draw.line((0, y, 1080, y), fill="#071727", width=1)
    glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((640, -200, 1300, 460), fill=(34, 197, 255, 65))
    glow = glow.filter(ImageFilter.GaussianBlur(110))
    bg = Image.alpha_composite(bg.convert("RGBA"), glow)
    draw = ImageDraw.Draw(bg)
    draw.rounded_rectangle((60, 50, 340, 98), radius=18, fill="#07121f", outline="#22c5ff", width=2)
    draw.text((84, 61), "AI 生成内容", font=font(24), fill="#91a6bb")
    title_lines = wrapped(draw, args.title, font(64), 900)[:2]
    y = 132
    for line in title_lines:
        draw.text((60, y), line, font=font(64), fill="#f4f8ff")
        y += 84
    background = assets / "background.png"
    bg.convert("RGB").save(background)

    overlay_inputs: list[Path] = []
    overlay_filters: list[tuple[int, int, float, float]] = []
    for index, entry in enumerate(cards):
        image = Image.new("RGBA", (960, 1055), (0, 0, 0, 0))
        card = ImageDraw.Draw(image)
        card.rounded_rectangle((0, 260, 960, 910), radius=42, fill="#07121feF", outline="#22c5ff", width=3)
        kicker = str(entry.get("kicker", "重点"))
        card.text((54, 310), kicker, font=font(29), fill="#22c5ff")
        cy = 370
        for line in wrapped(card, str(entry.get("title", "")), font(54), 850)[:3]:
            card.text((54, cy), line, font=font(54), fill="#f4f8ff")
            cy += 70
        cy += 20
        for line in wrapped(card, str(entry.get("body", "")), font(32), 850)[:7]:
            card.text((54, cy), line, font=font(32), fill="#91a6bb")
            cy += 48
        path = assets / f"card-{index + 1:03d}.png"
        image.save(path)
        overlay_inputs.append(path)
        overlay_filters.append((60, 80, float(entry["start"]), float(entry["end"])))
    for index, entry in enumerate(captions):
        image = Image.new("RGBA", (960, 88), (0, 0, 0, 0))
        caption = ImageDraw.Draw(image)
        text = str(entry.get("text", "")).strip().replace("\n", " ")
        if not text:
            continue
        caption.rounded_rectangle((0, 0, 960, 88), radius=24, fill=(3, 9, 17, 220))
        bbox = caption.textbbox((0, 0), text, font=font(44))
        x = max(20, (960 - (bbox[2] - bbox[0])) // 2)
        caption.text((x, 17), text, font=font(44), fill="#f4f4f1")
        path = assets / f"caption-{index + 1:04d}.png"
        image.save(path)
        overlay_inputs.append(path)
        overlay_filters.append((60, 1165, float(entry["start"]), float(entry["end"])))

    master = out / "packaged-master.mp4"
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(args.source), "-loop", "1", "-framerate", "30", "-t", f"{duration:.3f}", "-i", str(background)]
    for path in overlay_inputs:
        command.extend(["-loop", "1", "-framerate", "30", "-t", f"{duration:.3f}", "-i", str(path)])
    chain = ["[1:v]scale=1080:1920[base]", "[0:v]scale=450:445:force_original_aspect_ratio=increase,crop=450:445,eq=brightness=-0.08:contrast=1.05:saturation=0.9[person]", "[base][person]overlay=580:1285[tmp0]"]
    previous = "tmp0"
    for input_index, (x, y, start, end) in enumerate(overlay_filters, start=2):
        current = f"tmp{input_index - 1}"
        chain.append(f"[{previous}][{input_index}:v]overlay={x}:{y}:enable='gte(t,{start:.3f})*lt(t,{end:.3f})'[{current}]")
        previous = current
    chain.extend([f"[{previous}]fps=30,format=yuv420p[v]", "[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a]"])
    command.extend(["-filter_complex", ";".join(chain), "-map", "[v]", "-map", "[a]", "-t", f"{duration:.3f}", "-shortest", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(master)])
    rendered = run(command)
    if rendered.returncode != 0 or not master.is_file():
        raise RuntimeError("剪辑包装渲染未完成：" + (rendered.stderr.strip().splitlines()[-1] if rendered.stderr.strip() else "FFmpeg 未生成文件"))

    frame = assets / "cover-source.png"
    extracted = run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{min(0.5, duration / 2):.3f}", "-i", str(args.source), "-frames:v", "1", str(frame)])
    if extracted.returncode != 0 or not frame.is_file():
        raise RuntimeError("无法从来源视频取得授权封面人物画面")
    person = Image.open(frame).convert("RGB")

    def cover(width: int, height: int, name: str) -> Path:
        canvas = Image.new("RGB", (width, height), "#020711")
        cd = ImageDraw.Draw(canvas)
        for gx in range(0, width, max(40, width // 18)):
            cd.line((gx, 0, gx, height), fill="#071727", width=1)
        for gy in range(0, height, max(40, height // 18)):
            cd.line((0, gy, width, gy), fill="#071727", width=1)
        scale = max(width * 0.44 / person.width, height * 0.58 / person.height)
        resized = person.resize((int(person.width * scale), int(person.height * scale)), Image.Resampling.LANCZOS)
        crop_x = max(0, (resized.width - int(width * 0.44)) // 2)
        crop_y = max(0, (resized.height - int(height * 0.58)) // 2)
        portrait = resized.crop((crop_x, crop_y, crop_x + int(width * 0.44), crop_y + int(height * 0.58)))
        canvas.paste(portrait, (width - portrait.width - int(width * 0.04), height - portrait.height - int(height * 0.04)))
        cd = ImageDraw.Draw(canvas)
        cd.rounded_rectangle((int(width * 0.06), int(height * 0.07), int(width * 0.34), int(height * 0.12)), radius=16, fill="#07121f", outline="#22c5ff", width=2)
        cd.text((int(width * 0.085), int(height * 0.078)), "AI 生成内容", font=font(max(20, int(width * 0.022))), fill="#91a6bb")
        cy = int(height * 0.18)
        title_font = font(max(46, int(width * 0.065)))
        for line in wrapped(cd, args.title, title_font, int(width * 0.82))[:4]:
            cd.text((int(width * 0.06), cy), line, font=title_font, fill="#f4f8ff")
            cy += int(width * 0.085)
        cd.rectangle((int(width * 0.06), cy + 12, int(width * 0.28), cy + 24), fill="#22c5ff")
        path = covers / name
        canvas.save(path)
        return path

    cover_916 = cover(1080, 1920, "cover-9x16.png")
    cover_34 = cover(1080, 1440, "cover-3x4.png")
    cover_11 = cover(1080, 1080, "cover-1x1.png")
    published = out / "packaged-with-cover.mp4"
    publish = run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "30", "-t", "0.1", "-i", str(cover_916), "-i", str(master), "-filter_complex", "[0:v]scale=1080:1920,format=yuv420p,trim=duration=0.1,setpts=PTS-STARTPTS[c];[1:v]setpts=PTS-STARTPTS[v];[c][v]concat=n=2:v=1:a=0[cv];[1:a]aresample=48000,adelay=100|100[a]", "-map", "[cv]", "-map", "[a]", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(published)])
    if publish.returncode != 0 or not published.is_file():
        raise RuntimeError("带封面发布版没有生成：" + (publish.stderr.strip().splitlines()[-1] if publish.stderr.strip() else "FFmpeg 未生成文件"))

    for label, media_path, minimum_duration in (("无封面母版", master, duration - 0.05), ("带封面发布版", published, duration)):
        verified = run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(media_path)])
        if verified.returncode != 0:
            raise RuntimeError(f"{label}无法通过媒体验收")
        data = json.loads(verified.stdout)
        video_stream = next((item for item in data.get("streams", []) if item.get("codec_type") == "video"), {})
        audio_stream = next((item for item in data.get("streams", []) if item.get("codec_type") == "audio"), {})
        actual_duration = float(data.get("format", {}).get("duration", 0))
        if video_stream.get("codec_name") != "h264" or video_stream.get("width") != 1080 or video_stream.get("height") != 1920 or audio_stream.get("codec_name") != "aac" or actual_duration < minimum_duration:
            raise RuntimeError(f"{label}技术参数未通过验收")

    qa = out / "qa-report.md"
    qa.write_text("# 剪辑包装 QA\n\n- [x] 1080×1920、30fps、H.264、AAC\n- [x] 人物窗口位于右下角\n- [x] 黑色背景与青蓝强调\n- [x] 无封面母版与带封面发布版已生成\n- [x] 9:16、3:4、1:1 三张封面已生成\n- [x] AI 生成内容标识已保留\n- [x] 所有交付文件已写入 SHA-256 清单\n", encoding="utf-8")
    output_items = [
        ("primary", master), ("published", published),
        ("cover_9x16", cover_916), ("cover_3x4", cover_34), ("cover_1x1", cover_11),
        ("content_hierarchy", args.content_hierarchy), ("cards", args.cards), ("captions", args.captions), ("qa", qa),
    ]
    inputs = [{"role": "source_video", "path": str(args.source), "sha256": sha256(args.source)}]
    if args.input_handoff:
        inputs.append({"role": "upstream_handoff", "path": str(args.input_handoff), "sha256": sha256(args.input_handoff)})
    delivery = {
        "schema_version": 1,
        "run_id": args.run_id,
        "stage": "packaging",
        "status": "qa_passed",
        "stage_skill": {"name": "digital-human-packaging-fixed", "version": "1.0.0"},
        "inputs": inputs,
        "source": {"path": str(args.source), "sha256": sha256(args.source)},
        "outputs": [{"role": role, "path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size} for role, path in output_items],
        "media": {"width": 1080, "height": 1920, "fps": 30, "video_codec": "h264", "audio_codec": "aac", "synthetic_disclosure": True},
        "limitations": [],
    }
    manifest = out / "delivery-manifest.json"
    manifest.write_text(json.dumps(delivery, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PACKAGING_COMPLETED", "master": str(master), "published": str(published), "manifest": str(manifest), "qa": str(qa)}, ensure_ascii=False))
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=default_config())
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--content-hierarchy", type=Path, required=True)
    parser.add_argument("--cards", type=Path, required=True)
    parser.add_argument("--captions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="standalone-packaging")
    parser.add_argument("--input-handoff", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    for name in ("config", "source", "content_hierarchy", "cards", "captions", "output_dir"):
        setattr(args, name, getattr(args, name).expanduser().resolve())
    if args.input_handoff:
        args.input_handoff = args.input_handoff.expanduser().resolve()
        if not args.input_handoff.is_file():
            print("剪辑包装的上游交接文件不存在。", file=sys.stderr)
            return 2
    if args.worker:
        try:
            return worker(args)
        except Exception as exc:
            print(f"剪辑包装未完成：{exc}", file=sys.stderr)
            return 2
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        python_path = Path(config["python"]).expanduser().resolve()
    except (OSError, KeyError, json.JSONDecodeError):
        print("剪辑包装运行环境尚未准备，请先运行 setup_runtime.py。", file=sys.stderr)
        return 2
    command = [str(python_path), str(Path(__file__).resolve()), "--worker", "--config", str(args.config), "--source", str(args.source), "--title", args.title, "--content-hierarchy", str(args.content_hierarchy), "--cards", str(args.cards), "--captions", str(args.captions), "--output-dir", str(args.output_dir), "--run-id", args.run_id]
    if args.input_handoff:
        command.extend(["--input-handoff", str(args.input_handoff)])
    completed = run(command)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        print((detail[-1] if detail else "剪辑包装未完成。") + " 修正素材或环境后可以安全重试。", file=sys.stderr)
        return 2
    print(completed.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
