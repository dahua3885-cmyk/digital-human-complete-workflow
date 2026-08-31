#!/usr/bin/env python3
"""Render one authorized lip-synced MP4 with a registered MuseTalk 1.5 runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from check_runtime import default_config, hidden_flags, inspect


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(ffprobe: str, media: Path) -> dict[str, object]:
    completed = subprocess.run(
        [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(media)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=hidden_flags(),
    )
    return json.loads(completed.stdout)


def duration(payload: dict[str, object]) -> float:
    raw = payload.get("format", {})
    return float(raw.get("duration", 0)) if isinstance(raw, dict) else 0.0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime-config", type=Path, default=default_config())
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    video = args.video.expanduser().resolve()
    audio = args.audio.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not video.is_file() or not audio.is_file():
        print("数字人画面输入不完整：请提供有效的参考视频和已确认音频。", file=sys.stderr)
        return 2
    runtime = inspect(args.runtime_config.expanduser().resolve())
    if not runtime["ready"]:
        print("数字人画面暂时不能开始：" + "；".join(runtime["problems_zh"]) + "。", file=sys.stderr)
        return 2

    plan = {
        "provider": "official-musetalk-1.5",
        "video_sha256": sha256(video),
        "audio_sha256": sha256(audio),
        "output": str(output),
        "fps": args.fps,
        "batch_size": args.batch_size,
    }
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dh-avatar-") as temporary:
        job = Path(temporary)
        staged_video = job / ("input" + (video.suffix.lower() or ".mp4"))
        staged_audio = job / ("audio" + (audio.suffix.lower() or ".wav"))
        shutil.copyfile(video, staged_video)
        shutil.copyfile(audio, staged_audio)
        config = job / "job.yaml"
        config.write_text(
            "task_0:\n"
            f'  video_path: "{staged_video.as_posix()}"\n'
            f'  audio_path: "{staged_audio.as_posix()}"\n'
            '  result_name: "digital_human.mp4"\n'
            "  bbox_shift: 0\n",
            encoding="ascii",
        )
        result_dir = job / "results"
        command = [
            str(runtime["python"]),
            "-m",
            "scripts.inference",
            "--inference_config",
            str(config),
            "--result_dir",
            str(result_dir),
            "--unet_model_path",
            "models/musetalkV15/unet.pth",
            "--unet_config",
            "models/musetalkV15/musetalk.json",
            "--version",
            "v15",
            "--use_float16",
            "--batch_size",
            str(args.batch_size),
            "--fps",
            str(args.fps),
            "--parsing_mode",
            "jaw",
            "--left_cheek_width",
            "90",
            "--right_cheek_width",
            "90",
            "--ffmpeg_path",
            str(Path(str(runtime["ffmpeg"])).parent),
        ]
        stdout_path = job / "musetalk.out.log"
        stderr_path = job / "musetalk.err.log"
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
            completed = subprocess.run(
                command,
                cwd=runtime["repo"],
                stdout=stdout,
                stderr=stderr,
                creationflags=hidden_flags(),
            )
        expected = result_dir / "v15" / "digital_human.mp4"
        if completed.returncode != 0 or not expected.is_file() or expected.stat().st_size == 0:
            tail = stderr_path.read_text(encoding="utf-8", errors="replace")[-1200:]
            print("数字人画面生成没有完成。运行日志末尾：" + tail, file=sys.stderr)
            return 2
        shutil.copyfile(expected, output)

    video_probe = probe(str(runtime["ffprobe"]), output)
    audio_probe = probe(str(runtime["ffprobe"]), audio)
    streams = video_probe.get("streams", [])
    codecs = {item.get("codec_type"): item.get("codec_name") for item in streams if isinstance(item, dict)}
    duration_delta = abs(duration(video_probe) - duration(audio_probe))
    if codecs.get("video") != "h264" or codecs.get("audio") != "aac" or duration_delta > 0.10:
        print(
            f"数字人画面已生成，但技术验收未通过：编码={codecs}，音画时长差={duration_delta:.3f}秒。",
            file=sys.stderr,
        )
        return 2
    result = {
        **plan,
        "status": "completed",
        "output_sha256": sha256(output),
        "codecs": codecs,
        "duration_seconds": duration(video_probe),
        "audio_video_duration_delta_seconds": duration_delta,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
