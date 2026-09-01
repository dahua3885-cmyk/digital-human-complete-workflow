#!/usr/bin/env python3
"""Validate and save a local lawful-use and voice/likeness consent record."""

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


def atomic_json(path: Path, payload: dict[str, object]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def validate(record: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        return ["授权记录格式或版本不正确"]
    if record.get("lawful_use_confirmed") is not True:
        errors.append("尚未明确确认本次用途合法")
    subject = record.get("subject")
    permissions = record.get("permissions")
    notice = record.get("notice")
    evidence = record.get("evidence")
    revocation = record.get("revocation")
    if not isinstance(subject, dict) or subject.get("relationship") not in {"self", "third_party"} or not str(subject.get("name", "")).strip():
        errors.append("请填写人物称呼，并注明是本人还是第三方")
    if not isinstance(permissions, dict):
        errors.append("缺少分项授权")
    else:
        for key, label in (("voice_clone", "声音克隆"), ("likeness_lip_sync", "肖像嘴部驱动"), ("video_editing", "剪辑包装"), ("publication", "发布")):
            if permissions.get(key) is not True:
                errors.append(f"尚未确认{label}授权")
        if not isinstance(permissions.get("platforms"), list) or not permissions.get("platforms"):
            errors.append("请填写允许发布的平台")
        if not str(permissions.get("territory", "")).strip() or str(permissions.get("territory", "")).startswith("replace-"):
            errors.append("请填写授权地区")
    if not isinstance(notice, dict):
        errors.append("缺少处理目的与风险告知")
    else:
        if not str(notice.get("purpose", "")).strip() or str(notice.get("purpose", "")).startswith("replace-"):
            errors.append("请填写本次制作目的")
        if notice.get("rights_and_risks_explained") is not True:
            errors.append("尚未确认权利、风险和撤回方式已经说明")
        if not str(notice.get("retention", "")).strip() or str(notice.get("retention", "")).startswith("replace-"):
            errors.append("请填写本地素材保存期限")
    if not isinstance(evidence, dict) or evidence.get("confirmed") is not True or not str(evidence.get("confirmation_text", "")).strip() or not str(evidence.get("confirmed_at", "")).strip():
        errors.append("请填写授权确认原话和确认时间")
    elif isinstance(subject, dict) and subject.get("relationship") == "third_party":
        path_value = evidence.get("path")
        declared = evidence.get("sha256")
        path = Path(path_value).expanduser().resolve() if isinstance(path_value, str) and path_value else None
        if path is None or not path.is_file():
            errors.append("第三方人物必须提供可验证的授权证据文件")
        elif not isinstance(declared, str) or sha256(path).lower() != declared.lower():
            errors.append("第三方授权证据 SHA-256 与文件不一致")
    if not isinstance(revocation, dict) or not str(revocation.get("method", "")).strip() or str(revocation.get("method", "")).startswith("replace-"):
        errors.append("请填写撤回授权的方式")
    return errors


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    workspace = args.workspace.expanduser().resolve()
    status_path = workspace / "profiles" / "onboarding-status.json"
    try:
        record = json.loads(args.record.expanduser().resolve().read_text(encoding="utf-8"))
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"授权资料无法读取：{exc}", file=sys.stderr)
        return 2
    errors = validate(record)
    if errors:
        print("授权资料还缺少：" + "；".join(errors) + "。只需补充这些具体项目，不需要重填个人资料。", file=sys.stderr)
        return 2
    destination = workspace / ".private" / "consent" / "consent-record.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    record["validated_at"] = datetime.now(timezone.utc).isoformat()
    atomic_json(destination, record)
    status["lawful_use_declaration"] = "verified"
    status["identity_authorization"] = "verified"
    status["updated_at"] = datetime.now(timezone.utc).isoformat()
    atomic_json(status_path, status)
    print("合法使用与声音、肖像授权记录已在本机建立。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
