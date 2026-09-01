#!/usr/bin/env python3
"""把用户提供的外部文案、音频或视频登记为可验证入口交接文件。"""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): value.update(block)
    return value.hexdigest()

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"): sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True); parser.add_argument("--kind", choices=("script", "audio", "avatar"), required=True)
    parser.add_argument("--file", type=Path, required=True); parser.add_argument("--provided-by", required=True)
    parser.add_argument("--authorization-text", required=True); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        source = args.file.expanduser().resolve()
        if not source.is_file() or source.stat().st_size <= 0: raise ValueError("外部输入文件不存在或为空")
        payload = {"schema_version": 1, "run_id": args.run_id, "stage": args.kind, "status": "approved", "stage_skill": {"name": "external-user-input", "version": "1"}, "created_at": datetime.now(timezone.utc).isoformat(), "inputs": [], "outputs": [{"role": "primary", "path": str(source), "sha256": sha256(source), "bytes": source.stat().st_size}], "approval": {"required": True, "approved_by": args.provided_by, "approval_text": "用户提供并确认直接使用"}, "authorization": {"provided_by": args.provided_by, "text": args.authorization_text}, "limitations": ["此文件是用户提供的外部输入，不代表任何上游生成 Skill 已执行"]}
        output = args.output.expanduser().resolve(); output.parent.mkdir(parents=True, exist_ok=True); temporary = output.with_suffix(output.suffix + ".tmp"); temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); os.replace(temporary, output)
        print(f"外部输入交接文件已建立：{output}"); return 0
    except (OSError, ValueError) as exc:
        print(f"无法建立外部输入交接文件：{exc}", file=sys.stderr); return 2

if __name__ == "__main__": raise SystemExit(main())
