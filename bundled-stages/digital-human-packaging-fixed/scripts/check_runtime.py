#!/usr/bin/env python3
"""Check the fixed public packaging runtime."""

from __future__ import annotations

import argparse
import json
import os
import shutil
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


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=default_config())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    problems: list[str] = []
    try:
        config = json.loads(args.config.expanduser().resolve().read_text(encoding="utf-8"))
    except FileNotFoundError:
        config = {}
        problems.append("尚未准备剪辑包装运行环境")
    except (OSError, UnicodeError, json.JSONDecodeError):
        config = {}
        problems.append("剪辑包装运行配置无法读取或格式不正确")
    ffmpeg = config.get("ffmpeg") or shutil.which("ffmpeg")
    ffprobe = config.get("ffprobe") or shutil.which("ffprobe")
    python_path = Path(str(config.get("python", ""))).expanduser()
    font = Path(str(config.get("font", ""))).expanduser()
    if not ffmpeg or not Path(str(ffmpeg)).is_file():
        problems.append("没有找到 FFmpeg")
    if not ffprobe or not Path(str(ffprobe)).is_file():
        problems.append("没有找到 FFprobe")
    if not python_path.is_file():
        problems.append("剪辑包装专用 Python 环境不存在")
    else:
        check = subprocess.run([str(python_path), "-c", "from PIL import Image, ImageDraw, ImageFont"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=hidden_flags())
        if check.returncode != 0:
            problems.append("剪辑包装 Python 环境无法加载 Pillow")
    if not font.is_file():
        problems.append("剪辑包装中文字体尚未准备")
    payload = {"ready": not problems, "provider": "ffmpeg-pillow-fixed-layout", "config_path": str(args.config), "problems_zh": problems}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif payload["ready"]:
        print("剪辑包装运行环境已准备完成。")
    else:
        print("剪辑包装暂时不能开始：" + "；".join(problems) + "。")
    return 0 if payload["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
