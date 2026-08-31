#!/usr/bin/env python3
"""Install or register a pinned official MuseTalk 1.5 runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


UPSTREAM = "https://github.com/TMElyralab/MuseTalk.git"
PINNED_COMMIT = "0a89dec45a0192b824e3cf4daf96c239440c5ed8"
STAGE_ROOT = Path(__file__).resolve().parent.parent
VENDOR_ROOT = STAGE_ROOT / "vendor" / "MuseTalk"
VENDOR_MANIFEST = STAGE_ROOT / "vendor" / "manifest.json"
OVERLAY_ROOT = STAGE_ROOT / "overlays" / "portable-inference"
OVERLAY_MANIFEST = STAGE_ROOT / "overlays" / "manifest.json"
RUNTIME_REQUIREMENTS = STAGE_ROOT / "assets" / "requirements-runtime.txt"
MODEL_DOWNLOADER = STAGE_ROOT / "scripts" / "download_public_models.py"
MINIMUM_FREE_BYTES = 10 * 1024 * 1024 * 1024


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
    local_app_data = Path(os.getenv("LOCALAPPDATA", ""))
    program_files = Path(os.getenv("ProgramFiles", ""))
    common = [
        local_app_data / "Programs" / "Python" / "Python310" / "python.exe",
        program_files / "Python310" / "python.exe",
    ]
    for path in common:
        if path.is_file():
            return [str(path.resolve())]
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


def find_media_command(name: str) -> str | None:
    explicit = os.getenv("FFMPEG_PATH")
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_dir():
            candidate = candidate / (name + (".exe" if os.name == "nt" else ""))
        if candidate.is_file():
            return str(candidate.resolve())
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        package_root = Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
        if package_root.is_dir():
            matches = sorted(package_root.glob(f"Gyan.FFmpeg_*/*/bin/{name}.exe"), reverse=True)
            if matches:
                return str(matches[0].resolve())
    return None


def tree_sha256(root: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        digest.update(b"\0")
    return len(files), digest.hexdigest()


def verify_vendor() -> dict[str, object]:
    try:
        manifest = json.loads(VENDOR_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"内置 MuseTalk 引擎清单无法读取：{exc}") from exc
    if not (VENDOR_ROOT / "scripts" / "inference.py").is_file():
        raise RuntimeError("安装包缺少内置 MuseTalk 推理引擎。")
    count, digest = tree_sha256(VENDOR_ROOT)
    if count != manifest.get("file_count") or digest != manifest.get("tree_sha256"):
        raise RuntimeError("内置 MuseTalk 推理引擎校验失败，请重新下载 Skill。")
    return manifest


def verify_overlay() -> dict[str, object]:
    try:
        manifest = json.loads(OVERLAY_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"便携推理补丁清单无法读取：{exc}") from exc
    count, digest = tree_sha256(OVERLAY_ROOT)
    if count != manifest.get("file_count") or digest != manifest.get("tree_sha256"):
        raise RuntimeError("便携推理补丁校验失败，请重新下载 Skill。")
    return manifest


def prepare_engine(repo: Path, vendor: dict[str, object], overlay: dict[str, object]) -> None:
    marker = repo / ".codex-public-engine.json"
    if repo.exists():
        try:
            existing = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise RuntimeError(
                f"运行目录已存在但不是本安装器管理的公开引擎：{repo}。"
                "请换一个 --runtime-root，或使用 --register-existing-repo 登记已有环境。"
            )
        if (
            existing.get("tree_sha256") != vendor.get("tree_sha256")
            or existing.get("overlay_tree_sha256") != overlay.get("tree_sha256")
        ):
            raise RuntimeError("已有公开引擎版本与当前安装包不一致，请换一个新的运行目录。")
        return
    shutil.copytree(VENDOR_ROOT, repo)
    shutil.copytree(OVERLAY_ROOT, repo, dirs_exist_ok=True)
    marker.write_text(
        json.dumps(
            {
                "upstream": UPSTREAM,
                "commit": PINNED_COMMIT,
                "tree_sha256": vendor["tree_sha256"],
                "overlay_tree_sha256": overlay["tree_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_config(root: Path, repo: Path, python_path: Path) -> Path:
    config = root / "runtime.json"
    payload = {
        "schema_version": 1,
        "provider": "official-musetalk-1.5",
        "upstream": UPSTREAM,
        "commit": PINNED_COMMIT,
        "repo": str(repo.resolve()),
        "python": str(python_path.resolve()),
        "ffmpeg": find_media_command("ffmpeg") or "ffmpeg",
        "ffprobe": find_media_command("ffprobe") or "ffprobe",
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
    parser.add_argument("--accept-system-changes", action="store_true")
    parser.add_argument("--prepare-engine-only", action="store_true", help="Copy and verify the bundled public engine without installing models")
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

    if args.accept_system_changes and sys.platform == "win32":
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if not powershell:
            print("没有找到 PowerShell，无法自动准备 Windows 公共依赖。", file=sys.stderr)
            return 2
        run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(STAGE_ROOT / "scripts" / "setup_windows_prerequisites.ps1"),
                "-AcceptSystemChanges",
            ]
        )

    try:
        vendor = verify_vendor()
        overlay = verify_overlay()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.prepare_engine_only:
        root.mkdir(parents=True, exist_ok=True)
        repo = root / "MuseTalk"
        try:
            prepare_engine(repo, vendor, overlay)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(f"随包 MuseTalk 公开推理引擎已准备并校验：{repo}")
        return 0

    requirements = {
        "platform": sys.platform,
        "ffmpeg": find_media_command("ffmpeg"),
        "ffprobe": find_media_command("ffprobe"),
        "nvidia_smi": shutil.which("nvidia-smi"),
        "python_3_10": find_python310(),
        "upstream": UPSTREAM,
        "commit": PINNED_COMMIT,
        "engine_bundled": True,
        "engine_tree_sha256": vendor["tree_sha256"],
        "portable_overlay_tree_sha256": overlay["tree_sha256"],
        "runtime_root": str(root),
    }
    if args.dry_run:
        print(json.dumps(requirements, ensure_ascii=False, indent=2))
        return 0
    if not args.accept_large_download:
        print(
            "MuseTalk 推理引擎已经随 Skill 提供；首次准备仍会下载数 GB 的 Python 依赖和公开模型。请确认磁盘、网络和 NVIDIA GPU 后，使用 --accept-large-download 继续。",
            file=sys.stderr,
        )
        return 2
    if sys.platform not in {"win32", "linux"}:
        print("当前自动安装器只支持经过上游说明覆盖的 Windows 或 Linux。", file=sys.stderr)
        return 2
    missing = [key for key in ("ffmpeg", "ffprobe", "nvidia_smi", "python_3_10") if not requirements[key]]
    if missing:
        labels = {
            "ffmpeg": "FFmpeg",
            "ffprobe": "FFprobe",
            "nvidia_smi": "NVIDIA 驱动",
            "python_3_10": "Python 3.10",
        }
        print("暂时不能安装 MuseTalk，缺少：" + "、".join(labels[item] for item in missing) + "。", file=sys.stderr)
        if sys.platform == "win32" and any(item in missing for item in ("ffmpeg", "ffprobe", "python_3_10")):
            print("可重新运行并增加 --accept-system-changes，让安装器通过 winget 准备 Python 3.10 与 FFmpeg。", file=sys.stderr)
        return 2

    existing_parent = root
    while not existing_parent.exists() and existing_parent != existing_parent.parent:
        existing_parent = existing_parent.parent
    free_bytes = shutil.disk_usage(existing_parent).free
    if free_bytes < MINIMUM_FREE_BYTES:
        print(
            f"数字人公开模型和专用环境至少需要约 10 GB 可用空间；当前目标磁盘只剩 {free_bytes / 1024**3:.1f} GB。"
            "请使用 --runtime-root 选择空间更充足的本机目录。",
            file=sys.stderr,
        )
        return 2

    root.mkdir(parents=True, exist_ok=True)
    repo = root / "MuseTalk"
    try:
        prepare_engine(repo, vendor, overlay)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    venv = root / "venv"
    python_command = list(requirements["python_3_10"])
    if not venv.exists():
        run(python_command + ["-m", "venv", str(venv)])
    python_path = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    install_env = dict(os.environ)
    install_env["PIP_NO_CACHE_DIR"] = "1"
    install_env["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], env=install_env)
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
        ],
        env=install_env,
    )
    run([str(python_path), "-m", "pip", "install", "-r", str(RUNTIME_REQUIREMENTS)], env=install_env)
    run([str(python_path), str(MODEL_DOWNLOADER), "--repo", str(repo)], env=install_env)

    config = write_config(root, repo, python_path)
    print(f"数字人画面运行环境已安装：{config}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
