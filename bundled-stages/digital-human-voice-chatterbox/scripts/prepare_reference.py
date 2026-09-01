#!/usr/bin/env python3
"""Extract and grade an authorized voice-reference clip."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path


def hidden_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=hidden_flags())


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--duration", type=float, default=10.0)
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not source.is_file():
        print("参考声音或视频文件不存在。", file=sys.stderr)
        return 2
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("没有找到 FFmpeg，暂时不能提取参考声音。", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(max(0, args.start)), "-i", str(source), "-t", str(max(0.1, args.duration)), "-vn", "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(output)]
    completed = run(command)
    if completed.returncode != 0 or not output.is_file():
        print("参考声音提取未完成：" + (completed.stderr.strip() or "无法读取素材") + "。", file=sys.stderr)
        return 2
    try:
        with wave.open(str(output), "rb") as stream:
            seconds = stream.getnframes() / float(stream.getframerate())
    except (OSError, wave.Error) as exc:
        print(f"参考声音无法读取：{exc}", file=sys.stderr)
        return 2
    problems: list[str] = []
    warnings: list[str] = []
    if seconds < 3.0:
        problems.append("有效语音短于 3 秒")
    elif seconds < 5.0:
        warnings.append("当前只有最低可尝试长度，音色相似度和稳定性可能较低")
    elif seconds > 15.0:
        warnings.append("当前片段较长，建议挑选 5–15 秒最干净的连续语音")
    payload = {"ready": not problems, "duration_seconds": round(seconds, 3), "reference_wav": str(output), "problems_zh": problems, "warnings_zh": warnings}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
