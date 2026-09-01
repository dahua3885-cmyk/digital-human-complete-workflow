#!/usr/bin/env python3
"""Create an approved audio handoff bound to its script input and QA."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def item(role: str, path: Path) -> dict[str, str]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"文件不存在：{path}")
    return {"role": role, "path": str(path), "sha256": sha256(path)}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--script-handoff", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--qa", type=Path, required=True)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--approval-text", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        script_handoff = args.script_handoff.expanduser().resolve()
        script_payload = json.loads(script_handoff.read_text(encoding="utf-8"))
        if script_payload.get("stage") != "script" or script_payload.get("status") != "approved" or script_payload.get("run_id") != args.run_id:
            raise ValueError("文案交接物与当前任务不匹配或尚未批准")
        payload = {
            "schema_version": 1,
            "run_id": args.run_id,
            "stage": "audio",
            "status": "approved",
            "stage_skill": {"name": "digital-human-voice-chatterbox", "version": "1.0.0"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "inputs": [item("script_handoff", script_handoff)],
            "outputs": [item("primary", args.audio), item("qa", args.qa)],
            "approval": {"required": True, "approved_by": args.approved_by, "approval_text": args.approval_text},
            "native_manifest": item("native_manifest", args.audio.with_suffix(".manifest.json")),
            "limitations": [],
        }
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_suffix(output.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, output)
        print(f"音频交接物已建立：{output}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"无法建立音频交接物：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
