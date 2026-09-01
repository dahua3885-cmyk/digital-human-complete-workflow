#!/usr/bin/env python3
"""建立绑定音频、授权、画面 QA 和用户确认的数字人画面交接文件。"""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): value.update(block)
    return value.hexdigest()

def item(role: str, path: Path) -> dict[str, object]:
    path = path.expanduser().resolve()
    if not path.is_file() or path.stat().st_size <= 0: raise ValueError(f"文件不存在或为空：{path}")
    return {"role": role, "path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"): sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True); parser.add_argument("--audio-handoff", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True); parser.add_argument("--qa", type=Path, required=True)
    parser.add_argument("--consent-record", type=Path, required=True); parser.add_argument("--approved-by", required=True)
    parser.add_argument("--approval-text", required=True); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        upstream = args.audio_handoff.expanduser().resolve(); data = json.loads(upstream.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or data.get("stage") != "audio" or data.get("status") != "approved" or data.get("run_id") != args.run_id:
            raise ValueError("音频交接文件与当前任务不匹配或尚未确认")
        consent = json.loads(args.consent_record.expanduser().resolve().read_text(encoding="utf-8"))
        if consent.get("lawful_use_confirmed") is not True or consent.get("permissions", {}).get("likeness_lip_sync") is not True or consent.get("evidence", {}).get("confirmed") is not True:
            raise ValueError("合法使用与肖像授权记录未通过验证")
        payload = {"schema_version": 1, "run_id": args.run_id, "stage": "avatar", "status": "approved", "stage_skill": {"name": "digital-human-avatar-musetalk", "version": "1.0.0"}, "created_at": datetime.now(timezone.utc).isoformat(), "inputs": [item("audio_handoff", upstream), item("consent_record", args.consent_record)], "outputs": [item("primary", args.video), item("qa", args.qa)], "approval": {"required": True, "approved_by": args.approved_by, "approval_text": args.approval_text}, "limitations": []}
        output = args.output.expanduser().resolve(); output.parent.mkdir(parents=True, exist_ok=True); temporary = output.with_suffix(output.suffix + ".tmp"); temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); os.replace(temporary, output)
        print(f"数字人画面交接文件已建立：{output}"); return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"无法建立数字人画面交接文件：{exc}", file=sys.stderr); return 2

if __name__ == "__main__": raise SystemExit(main())
