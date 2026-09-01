#!/usr/bin/env python3
"""Render Chinese cloned speech with the configured local Chatterbox runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


STYLES = {
    "natural": {"label": "自然均衡", "exaggeration": 0.50, "cfg_weight": 0.50},
    "steady": {"label": "稳健融合", "exaggeration": 0.35, "cfg_weight": 0.65},
    "compact": {"label": "短视频紧凑", "exaggeration": 0.65, "cfg_weight": 0.35},
}


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def split_text(text: str, maximum: int = 220) -> list[str]:
    """Split long Chinese scripts at semantic punctuation before model limits."""
    units = [item.strip() for item in re.split(r"(?<=[。！？；!?;])", text) if item.strip()]
    chunks: list[str] = []
    current = ""
    for unit in units:
        while len(unit) > maximum:
            head, unit = unit[:maximum], unit[maximum:]
            if current: chunks.append(current); current = ""
            chunks.append(head)
        if current and len(current) + len(unit) > maximum:
            chunks.append(current); current = unit
        else:
            current += unit
    if current: chunks.append(current)
    return chunks


def default_config() -> Path:
    explicit = os.getenv("DIGITAL_HUMAN_VOICE_RUNTIME")
    if explicit:
        return Path(explicit).expanduser().resolve()
    codex_home = Path(os.getenv("CODEX_HOME", Path.home() / ".codex"))
    return codex_home / "runtimes" / "digital-human-voice-chatterbox" / "runtime.json"


def hidden_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def worker(args: argparse.Namespace) -> int:
    import torch
    import torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    config = json.loads(args.config.read_text(encoding="utf-8"))
    model_dir = Path(config["model_dir"]).expanduser().resolve()
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    text = args.text_file.read_text(encoding="utf-8").strip()
    if not text:
        raise RuntimeError("口播文案为空")
    style = STYLES[args.style]
    model = ChatterboxMultilingualTTS.from_local(model_dir, device=device, t3_model="v3")
    chunks = split_text(text)
    parts = []
    for index, chunk in enumerate(chunks):
        part = model.generate(chunk, language_id=args.language, audio_prompt_path=str(args.reference_audio), exaggeration=style["exaggeration"], cfg_weight=style["cfg_weight"])
        parts.append(part)
        if index < len(chunks) - 1:
            parts.append(torch.zeros((part.shape[0], int(model.sr * 0.16)), dtype=part.dtype, device=part.device))
    wav = torch.cat(parts, dim=-1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torchaudio.save(str(args.output), wav, model.sr)
    manifest = {
        "schema_version": 1,
        "provider": "chatterbox-multilingual-v3",
        "model_revision": config.get("model_revision"),
        "style_id": args.style,
        "style_label": style["label"],
        "language": args.language,
        "device": device,
        "watermark": "Chatterbox Perth implicit watermark retained",
        "output": str(args.output),
        "output_sha256": sha256(args.output),
        "segments": len(chunks),
        "sample_rate": model.sr,
    }
    args.output.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=default_config())
    parser.add_argument("--text-file", type=Path, required=True)
    parser.add_argument("--reference-audio", type=Path, required=True)
    parser.add_argument("--style", choices=tuple(STYLES), required=True)
    parser.add_argument("--language", default="zh")
    parser.add_argument("--device", choices=("auto", "cuda", "cpu", "mps"), default="auto")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.config = args.config.expanduser().resolve()
    args.text_file = args.text_file.expanduser().resolve()
    args.reference_audio = args.reference_audio.expanduser().resolve()
    args.output = args.output.expanduser().resolve()
    if args.worker:
        try:
            return worker(args)
        except Exception as exc:
            print(f"数字人声音生成未完成：{exc}", file=sys.stderr)
            return 2
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        python_path = Path(config["python"]).expanduser().resolve()
    except (OSError, KeyError, json.JSONDecodeError):
        print("声音运行环境尚未准备完成，请先运行 setup_runtime.py。", file=sys.stderr)
        return 2
    command = [str(python_path), str(Path(__file__).resolve()), "--worker", "--config", str(args.config), "--text-file", str(args.text_file), "--reference-audio", str(args.reference_audio), "--style", args.style, "--language", args.language, "--device", args.device, "--output", str(args.output)]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=hidden_flags())
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        print((detail[-1] if detail else "数字人声音生成未完成。") + " 可修正素材或环境后安全重试。", file=sys.stderr)
        return 2
    print(completed.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
