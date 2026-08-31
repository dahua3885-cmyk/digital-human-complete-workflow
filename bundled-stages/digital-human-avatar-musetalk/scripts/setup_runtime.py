#!/usr/bin/env python3
"""Install or register a pinned official MuseTalk 1.5 runtime."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


UPSTREAM = "https://github.com/TMElyralab/MuseTalk.git"
PINNED_COMMIT = "0a89dec45a0192b824e3cf4daf96c239440c5ed8"


def hidden_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def runtime_root_default() -> Path:
    codex_home = Path(os.getenv("CODEX_HOME", Path.home() / ".codex"))
    return codex_home / "runtimes" / "digital-human-avatar-musetalk"


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        creationflags=hidden_flags(),
    )


def find_python310() -> list[str] | None:
    explicit = os.getenv("DIGITAL_HUMAN_PYTHON310")
    if explicit and Path(explicit).expanduser().is_file():
        return [str(Path(explicit).expanduser().resolve())]
    candidates = [["py", "-3.10"], ["python3.10"], ["python"]]
    for command in candidates:
        if shutil.which(command[0]) is None:
            continue
        check = subprocess.run(
            command + ["-c", "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 10) else 1)"],
            creationflags=hidden_flags(),
        )
        if check.returncode == 0:
            return command
    return None


def write_config(root: Path, repo: Path, python_path: Path) -> Path:
    config = root / "runtime.json"
    payload = {
        "schema_version": 1,
        "provider": "official-musetalk-1.5",
        "upstream": UPSTREAM,
        "commit": PINNED_COMMIT,
        "repo": str(repo.resolve()),
        "python": str(python_path.resolve()),
        "ffmpeg": shutil.which("ffmpeg") or "ffmpeg",
        "ffprobe": shutil.which("ffprobe") or "ffprobe",
    }
    temporary = config.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(config)
    return config


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=runtime_root_default())
    parser.add_argument("--accept-large-download", action="store_true")
    parser.add_argument("--register-existing-repo", type=Path)
    parser.add_argument("--register-existing-python", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.runtime_root.expanduser().resolve()
    if args.register_existing_repo or args.register_existing_python:
        if not args.register_existing_repo or not args.register_existing_python:
            print("登记已有环境时必须同时提供 MuseTalk 仓库和专用 Python。", file=sys.stderr)
            return 2
        repo = args.register_existing_repo.expanduser().resolve()
        python_path = args.register_existing_python.expanduser().resolve()
        if not (repo / "scripts" / "inference.py").is_file() or not python_path.is_file():
            print("已有 MuseTalk 仓库或 Python 路径无效。", file=sys.stderr)
            return 2
        root.mkdir(parents=True, exist_ok=True)
        config = write_config(root, repo, python_path)
        print(f"已登记数字人画面运行环境：{config}")
        return 0

    requirements = {
        "platform": sys.platform,
        "git": shutil.which("git"),
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "nvidia_smi": shutil.which("nvidia-smi"),
        "python_3_10": find_python310(),
        "upstream": UPSTREAM,
        "commit": PINNED_COMMIT,
        "runtime_root": str(root),
    }
    if args.dry_run:
        print(json.dumps(requirements, ensure_ascii=False, indent=2))
        return 0
    if not args.accept_large_download:
        print(
            "安装 MuseTalk 会下载数 GB 的代码、Python 依赖和模型。请确认磁盘、网络和 NVIDIA GPU 后，使用 --accept-large-download 继续。",
            file=sys.stderr,
        )
        return 2
    if sys.platform not in {"win32", "linux"}:
        print("当前自动安装器只支持经过上游说明覆盖的 Windows 或 Linux。", file=sys.stderr)
        return 2
    missing = [key for key in ("git", "ffmpeg", "ffprobe", "nvidia_smi", "python_3_10") if not requirements[key]]
    if missing:
        labels = {
            "git": "Git",
            "ffmpeg": "FFmpeg",
            "ffprobe": "FFprobe",
            "nvidia_smi": "NVIDIA 驱动",
            "python_3_10": "Python 3.10",
        }
        print("暂时不能安装 MuseTalk，缺少：" + "、".join(labels[item] for item in missing) + "。", file=sys.stderr)
        return 2

    root.mkdir(parents=True, exist_ok=True)
    repo = root / "MuseTalk"
    if not repo.exists():
        run([requirements["git"], "clone", UPSTREAM, str(repo)])
    run([requirements["git"], "fetch", "--tags", "origin"], cwd=repo)
    run([requirements["git"], "checkout", "--detach", PINNED_COMMIT], cwd=repo)

    venv = root / "venv"
    python_command = list(requirements["python_3_10"])
    if not venv.exists():
        run(python_command + ["-m", "venv", str(venv)])
    python_path = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"])
    run(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            "torch==2.0.1",
            "torchvision==0.15.2",
            "torchaudio==2.0.2",
            "--index-url",
            "https://download.pytorch.org/whl/cu118",
        ]
    )
    run([str(python_path), "-m", "pip", "install", "-r", str(repo / "requirements.txt")])
    run([str(python_path), "-m", "pip", "install", "--no-cache-dir", "-U", "openmim"])
    mim = venv / ("Scripts/mim.exe" if os.name == "nt" else "bin/mim")
    for package in ("mmengine", "mmcv==2.0.1", "mmdet==3.1.0", "mmpose==1.1.0"):
        run([str(mim), "install", package])

    child_env = dict(os.environ)
    child_env["PATH"] = str(python_path.parent) + os.pathsep + child_env.get("PATH", "")
    downloader = repo / ("download_weights.bat" if os.name == "nt" else "download_weights.sh")
    if os.name == "nt":
        run(["cmd", "/c", str(downloader)], cwd=repo, env=child_env)
    else:
        run(["bash", str(downloader)], cwd=repo, env=child_env)

    config = write_config(root, repo, python_path)
    print(f"数字人画面运行环境已安装：{config}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
