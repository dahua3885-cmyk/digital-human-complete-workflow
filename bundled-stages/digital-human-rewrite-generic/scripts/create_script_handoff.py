#!/usr/bin/env python3
"""Create a hash-bound approved script handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def file_item(role: str, path: Path) -> dict[str, str]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"文件不存在：{resolved}")
    return {"role": role, "path": str(resolved), "sha256": digest(resolved)}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-record", type=Path, required=True)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--qa", type=Path, required=True)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--approval-text", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        inputs = [file_item("source", args.source_record)]
        outputs = [file_item("primary", args.script), file_item("qa", args.qa)]
        payload = {
            "schema_version": 1,
            "run_id": args.run_id,
            "stage": "script",
            "status": "approved",
            "stage_skill": {"name": "digital-human-rewrite-generic", "version": "1.0.0"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "inputs": inputs,
            "outputs": outputs,
            "approval": {"required": True, "approved_by": args.approved_by, "approval_text": args.approval_text},
            "native_manifest": {"path": str(args.qa.resolve()), "sha256": digest(args.qa.resolve())},
            "limitations": [],
        }
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_suffix(output.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, output)
        print(f"文案交接物已建立：{output}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"无法建立文案交接物：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
