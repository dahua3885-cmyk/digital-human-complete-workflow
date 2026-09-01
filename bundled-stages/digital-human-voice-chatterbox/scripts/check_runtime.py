#!/usr/bin/env python3
"""Check the local Chatterbox voice runtime."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


REQUIRED_MODELS = (
    "ve.pt",
    "t3_mtl23ls_v3.safetensors",
    "s3gen.pt",
    "grapheme_mtl_merged_expanded_v1.json",
)


def default_config() -> Path:
    explicit = os.getenv("DIGITAL_HUMAN_VOICE_RUNTIME")
    if explicit:
        return Path(explicit).expanduser().resolve()
    codex_home = Path(os.getenv("CODEX_HOME", Path.home() / ".codex"))
    return codex_home / "runtimes" / "digital-human-voice-chatterbox" / "runtime.json"


def hidden_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def inspect(config_path: Path) -> dict[str, object]:
    problems: list[str] = []
    result: dict[str, object] = {"ready": False, "config_path": str(config_path), "problems_zh": problems}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        problems.append("尚未安装通用数字人声音运行环境")
        return result
    except (OSError, UnicodeError, json.JSONDecodeError):
        problems.append("声音运行配置无法读取或格式不正确")
        return result
    python_path = Path(str(data.get("python", ""))).expanduser()
    model_dir = Path(str(data.get("model_dir", ""))).expanduser()
    if not python_path.is_file():
        problems.append("声音专用 Python 环境不存在")
    else:
        check = subprocess.run(
            [str(python_path), "-c", "import chatterbox, torch, torchaudio; print(torch.__version__)"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=hidden_flags(),
        )
        if check.returncode != 0:
            problems.append("声音 Python 环境无法加载 Chatterbox、PyTorch 或 Torchaudio")
    if not model_dir.is_dir():
        problems.append("声音模型目录不存在")
    else:
        missing = [name for name in REQUIRED_MODELS if not (model_dir / name).is_file()]
        if missing:
            problems.append("声音模型文件不完整：" + "、".join(missing))
    result.update({"python": str(python_path), "model_dir": str(model_dir), "provider": data.get("provider")})
    result["ready"] = not problems
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=default_config())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = inspect(args.config.expanduser().resolve())
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ready"]:
        print("数字人声音运行环境已准备完成。")
    else:
        print("数字人声音暂时不能开始：" + "；".join(result["problems_zh"]) + "。")
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
