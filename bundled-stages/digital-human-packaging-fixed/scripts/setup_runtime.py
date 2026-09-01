#!/usr/bin/env python3
"""Prepare Pillow, FFmpeg discovery, and a pinned open Chinese font."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


FONT_URL = "https://raw.githubusercontent.com/notofonts/noto-cjk/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
FONT_SHA256 = "2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b"


def hidden_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def default_root() -> Path:
    codex_home = Path(os.getenv("CODEX_HOME", Path.home() / ".codex"))
    return codex_home / "runtimes" / "digital-human-packaging-fixed"


def find_media(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return str(Path(found).resolve())
    if os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
        matches = sorted(root.glob(f"Gyan.FFmpeg_*/*/bin/{name}.exe"), reverse=True) if root.is_dir() else []
        if matches:
            return str(matches[0].resolve())
    return None


def run(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=hidden_flags())
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        raise RuntimeError(detail[-1] if detail else "命令没有返回具体原因")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=default_root())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = args.runtime_root.expanduser().resolve()
    ffmpeg = find_media("ffmpeg")
    ffprobe = find_media("ffprobe")
    if args.dry_run:
        print(json.dumps({"runtime_root": str(root), "pillow": "12.3.0", "font_url": FONT_URL, "ffmpeg": ffmpeg, "ffprobe": ffprobe}, ensure_ascii=False, indent=2))
        return 0
    if not ffmpeg or not ffprobe:
        print("没有找到 FFmpeg/FFprobe。请先安装 FFmpeg，再重新运行本准备器。", file=sys.stderr)
        return 2
    root.mkdir(parents=True, exist_ok=True)
    venv = root / "venv"
    try:
        if not venv.exists():
            run([sys.executable, "-m", "venv", str(venv)])
        python_path = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run([str(python_path), "-m", "pip", "install", "--no-cache-dir", "Pillow==12.3.0"])
        font = root / "fonts" / "NotoSansCJKsc-Regular.otf"
        font.parent.mkdir(parents=True, exist_ok=True)
        if not font.is_file() or hashlib.sha256(font.read_bytes()).hexdigest() != FONT_SHA256:
            temp = font.with_suffix(".download")
            try:
                with urllib.request.urlopen(FONT_URL, timeout=60) as response, temp.open("wb") as stream:
                    shutil.copyfileobj(response, stream)
            except Exception as exc:
                if temp.exists():
                    temp.unlink()
                raise RuntimeError(f"中文字体下载未完成：{exc}") from exc
            if hashlib.sha256(temp.read_bytes()).hexdigest() != FONT_SHA256:
                temp.unlink()
                raise RuntimeError("中文字体校验失败")
            os.replace(temp, font)
        config = root / "runtime.json"
        config.write_text(json.dumps({"schema_version": 1, "provider": "ffmpeg-pillow-fixed-layout", "python": str(python_path), "ffmpeg": ffmpeg, "ffprobe": ffprobe, "font": str(font)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"剪辑包装运行环境已准备完成：{config}")
        return 0
    except (OSError, RuntimeError) as exc:
        print(f"剪辑包装运行环境没有准备完成：{exc}。网络恢复或依赖修复后可安全重试。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
