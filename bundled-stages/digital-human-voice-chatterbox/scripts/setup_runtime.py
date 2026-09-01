#!/usr/bin/env python3
"""Install a private, pinned Chatterbox runtime with concise Chinese errors."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


PACKAGE = "chatterbox-tts==0.1.7"
PERTH = "git+https://github.com/resemble-ai/Perth.git@f83052aa42a0a47b9b62ff041c6a9332945fdee4"
MODEL_REVISION = "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"
MINIMUM_FREE_BYTES = 8 * 1024 * 1024 * 1024
STAGE_ROOT = Path(__file__).resolve().parents[1]


def hidden_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def default_root() -> Path:
    codex_home = Path(os.getenv("CODEX_HOME", Path.home() / ".codex"))
    return codex_home / "runtimes" / "digital-human-voice-chatterbox"


def find_python() -> list[str] | None:
    explicit = os.getenv("DIGITAL_HUMAN_VOICE_PYTHON")
    if explicit and Path(explicit).expanduser().is_file():
        return [str(Path(explicit).expanduser().resolve())]
    candidates = [["py", "-3.11"], ["py", "-3.10"], ["py", "-3.12"], ["python3.11"], ["python3.10"], ["python"]]
    for command in candidates:
        if not shutil.which(command[0]):
            continue
        check = subprocess.run(
            command + ["-c", "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=hidden_flags(),
        )
        if check.returncode == 0:
            return command
    return None


def run(command: list[str], *, env: dict[str, str]) -> None:
    completed = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=hidden_flags(),
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        raise RuntimeError(detail[-1] if detail else "命令没有返回具体原因")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=default_root())
    parser.add_argument("--accept-large-download", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = args.runtime_root.expanduser().resolve()
    plan = {
        "provider": "chatterbox-multilingual-v3",
        "package": PACKAGE,
        "model_revision": MODEL_REVISION,
        "runtime_root": str(root),
        "minimum_free_gb": 8,
        "python": find_python(),
    }
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if not args.accept_large_download:
        print("首次准备数字人声音需要下载约数 GB 的公开模型与依赖。请确认网络和磁盘空间后，使用 --accept-large-download 继续。", file=sys.stderr)
        return 2
    if plan["python"] is None:
        print("没有找到 Python 3.10–3.13，暂时不能准备数字人声音运行环境。", file=sys.stderr)
        return 2
    parent = root
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    free = shutil.disk_usage(parent).free
    if free < MINIMUM_FREE_BYTES:
        print(f"声音模型和专用环境至少需要约 8 GB 可用空间；当前目标磁盘只剩 {free / 1024**3:.1f} GB。请使用 --runtime-root 选择空间更充足的本机目录。", file=sys.stderr)
        return 2
    root.mkdir(parents=True, exist_ok=True)
    venv = root / "venv"
    python_command = list(plan["python"])
    environment = dict(os.environ)
    environment["PIP_NO_CACHE_DIR"] = "1"
    environment["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    try:
        if not venv.exists():
            run(python_command + ["-m", "venv", str(venv)], env=environment)
        python_path = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], env=environment)
        run([str(python_path), "-m", "pip", "install", PACKAGE], env=environment)
        run([str(python_path), "-m", "pip", "install", "--force-reinstall", "--no-deps", PERTH], env=environment)
        model_dir = root / "models" / "chatterbox-multilingual-v3"
        run([str(python_path), str(STAGE_ROOT / "scripts" / "download_models.py"), "--model-dir", str(model_dir)], env=environment)
        config = root / "runtime.json"
        config.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "provider": "chatterbox-multilingual-v3",
                    "package": PACKAGE,
                    "model_revision": MODEL_REVISION,
                    "python": str(python_path),
                    "model_dir": str(model_dir),
                    "ffmpeg": shutil.which("ffmpeg") or "ffmpeg",
                    "ffprobe": shutil.which("ffprobe") or "ffprobe",
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        print(f"数字人声音运行环境已准备完成：{config}")
        return 0
    except (OSError, RuntimeError) as exc:
        print(f"数字人声音运行环境没有准备完成：{exc}。网络异常时恢复后可重新运行，已下载文件会继续复用。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
