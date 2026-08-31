#!/usr/bin/env python3
"""Validate the registered MuseTalk 1.5 runtime without exposing private media."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REQUIRED_REPO_FILES = (
    "scripts/inference.py",
    "models/musetalkV15/unet.pth",
    "models/musetalkV15/musetalk.json",
    "models/sd-vae/config.json",
    "models/sd-vae/diffusion_pytorch_model.bin",
    "models/whisper/config.json",
    "models/whisper/pytorch_model.bin",
    "models/face-parse-bisent/79999_iter.pth",
    "models/face-parse-bisent/resnet18-5c106cde.pth",
    "musetalk/utils/face_detection/detection/sfd/s3fd.pth",
)


def hidden_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def default_config() -> Path:
    explicit = os.getenv("DIGITAL_HUMAN_AVATAR_RUNTIME")
    if explicit:
        return Path(explicit).expanduser().resolve()
    codex_home = Path(os.getenv("CODEX_HOME", Path.home() / ".codex"))
    return codex_home / "runtimes" / "digital-human-avatar-musetalk" / "runtime.json"


def command_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve() if candidate.is_file() else None
    found = shutil.which(value)
    return Path(found).resolve() if found else None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect(config_path: Path, *, deep: bool = False) -> dict[str, object]:
    problems: list[str] = []
    result: dict[str, object] = {
        "ready": False,
        "config_path": str(config_path),
        "problems_zh": problems,
    }
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        problems.append("尚未登记 MuseTalk 1.5 本地运行环境")
        return result
    except (OSError, UnicodeError, json.JSONDecodeError):
        problems.append("MuseTalk 运行配置无法读取或格式不正确")
        return result

    repo_value = data.get("repo")
    repo = Path(repo_value).expanduser().resolve() if isinstance(repo_value, str) else None
    if repo is None or not repo.is_dir():
        problems.append("MuseTalk 仓库目录不存在")
    else:
        missing = [name for name in REQUIRED_REPO_FILES if not (repo / name).is_file()]
        if missing:
            problems.append("MuseTalk 代码或模型文件不完整：" + "、".join(missing))
        marker = repo / ".codex-public-engine.json"
        result["engine_source"] = "随 Skill 提供的公开 MuseTalk 引擎" if marker.is_file() else "使用者登记的已有 MuseTalk 环境"
        local_manifest = repo / "models-manifest.local.json"
        if marker.is_file() and not local_manifest.is_file():
            problems.append("公开模型尚未通过安装器下载和校验")
        elif local_manifest.is_file():
            try:
                model_data = json.loads(local_manifest.read_text(encoding="utf-8"))
                for item in model_data.get("files", []):
                    relative = item.get("path")
                    expected_size = item.get("bytes")
                    candidate = (repo / relative).resolve() if isinstance(relative, str) else None
                    if candidate is None or repo not in candidate.parents or not candidate.is_file():
                        problems.append("公开模型校验清单引用了无效文件")
                        break
                    if candidate.stat().st_size != expected_size:
                        problems.append(f"公开模型文件大小不一致：{relative}")
                        break
                    if deep and sha256(candidate) != item.get("sha256"):
                        problems.append(f"公开模型文件哈希不一致：{relative}")
                        break
            except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
                problems.append("公开模型校验清单无法读取")

    python_path = command_path(data.get("python"))
    if python_path is None:
        problems.append("MuseTalk 专用 Python 环境不存在")
    else:
        check = subprocess.run(
            [
                str(python_path),
                "-c",
                "import json, torch; print(json.dumps({'torch': torch.__version__, 'cuda': torch.cuda.is_available()}))",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=hidden_flags(),
        )
        if check.returncode != 0:
            problems.append("MuseTalk Python 环境无法加载 PyTorch")
        else:
            try:
                torch_info = json.loads(check.stdout.strip().splitlines()[-1])
                result["torch"] = torch_info.get("torch")
                result["cuda"] = bool(torch_info.get("cuda"))
                if not result["cuda"]:
                    problems.append("当前 MuseTalk Python 环境未检测到可用的 NVIDIA CUDA")
            except (IndexError, json.JSONDecodeError):
                problems.append("无法确认 MuseTalk 的 PyTorch 与 CUDA 状态")

    ffmpeg_path = command_path(data.get("ffmpeg", "ffmpeg"))
    ffprobe_path = command_path(data.get("ffprobe", "ffprobe"))
    if ffmpeg_path is None:
        problems.append("没有找到 FFmpeg")
    if ffprobe_path is None:
        problems.append("没有找到 FFprobe")

    result.update(
        {
            "repo": str(repo) if repo else None,
            "python": str(python_path) if python_path else None,
            "ffmpeg": str(ffmpeg_path) if ffmpeg_path else None,
            "ffprobe": str(ffprobe_path) if ffprobe_path else None,
        }
    )
    result["ready"] = not problems
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=default_config())
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--deep", action="store_true", help="Also hash every downloaded public model")
    args = parser.parse_args()
    result = inspect(args.config.expanduser().resolve(), deep=args.deep)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ready"]:
        print("数字人画面运行环境已准备完成。")
    else:
        print("数字人画面暂时不能开始：" + "；".join(result["problems_zh"]) + "。")
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
