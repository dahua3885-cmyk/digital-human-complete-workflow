#!/usr/bin/env python3
"""Create one resumable cross-stage task order in an initialized workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


STAGES = ("rewrite", "voice", "avatar", "packaging")
LABELS = {
    "rewrite": "开始二创",
    "voice": "开始数字人音频",
    "avatar": "开始数字人画面",
    "packaging": "开始剪辑包装",
}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--project", required=True, help="lowercase project slug")
    parser.add_argument("--entry", choices=STAGES, required=True)
    parser.add_argument("--target", choices=STAGES, required=True)
    parser.add_argument("--source-kind", choices=("url", "file", "text"), required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()

    if not SLUG_RE.fullmatch(args.project):
        print("ERROR: --project must use lowercase letters, digits, and hyphens", file=sys.stderr)
        return 2
    entry_index = STAGES.index(args.entry)
    target_index = STAGES.index(args.target)
    if entry_index > target_index:
        print("ERROR: target stage cannot be before entry stage", file=sys.stderr)
        return 2

    workspace = args.workspace.expanduser().resolve()
    asset_center = workspace / "profiles" / "asset-center.json"
    workflow_profile = workspace / "profiles" / "workflow-profile.json"
    projects = workspace / "projects"
    if not asset_center.is_file() or not workflow_profile.is_file() or not projects.is_dir():
        print(
            "ERROR: workspace is not initialized or an asset/workflow profile is missing",
            file=sys.stderr,
        )
        return 2
    try:
        workflow_payload = json.loads(workflow_profile.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read workflow profile: {exc}", file=sys.stderr)
        return 2
    stage_skills = workflow_payload.get("stage_skills")
    if not isinstance(stage_skills, dict):
        print("ERROR: workflow profile has no stage_skills object", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc)
    order_id = f"{now.strftime('%Y%m%d-%H%M%S')}-{args.project}"
    project_dir = projects / order_id
    if project_dir.exists():
        print(f"ERROR: task order already exists: {project_dir}", file=sys.stderr)
        return 2
    (project_dir / "handoffs").mkdir(parents=True)

    source_sha256 = None
    if args.source_kind == "file":
        source_path = Path(args.source).expanduser().resolve()
        if not source_path.is_file():
            print(f"ERROR: source file not found: {source_path}", file=sys.stderr)
            return 2
        source_value = str(source_path)
        source_sha256 = sha256(source_path)
    else:
        source_value = args.source

    stages: dict[str, object] = {}
    for index, stage in enumerate(STAGES):
        if index < entry_index or index > target_index:
            state = "skipped"
        elif index == entry_index:
            state = "ready"
        else:
            state = "queued"
        stages[stage] = {
            "state": state,
            "input_handoff": None,
            "output_handoff": None,
            "estimate": {
                "status": "required_before_start" if state in {"ready", "queued"} else "not_applicable",
                "low_minutes": None,
                "high_minutes": None,
                "basis": None,
                "calculated_at": None,
            },
            "failure": None,
        }

    order = {
        "schema_version": 1,
        "order_id": order_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "entry_stage": args.entry,
        "target_stage": args.target,
        "status": "ready",
        "current_stage": args.entry,
        "source": {
            "kind": args.source_kind,
            "value": source_value,
            "sha256": source_sha256,
        },
        "asset_center": {
            "path": str(Path("..") / ".." / "profiles" / "asset-center.json"),
            "snapshot_sha256": sha256(asset_center),
        },
        "workflow_profile": {
            "path": str(Path("..") / ".." / "profiles" / "workflow-profile.json"),
            "snapshot_sha256": sha256(workflow_profile),
        },
        "stage_skills": stage_skills,
        "stages": stages,
        "next_action": {
            "type": "estimate_and_start",
            "stage": args.entry,
            "label": LABELS[args.entry],
        },
        "history": [
            {
                "at": now.isoformat(),
                "event": "order_created",
                "stage": args.entry,
            }
        ],
    }
    order_path = project_dir / "task-order.json"
    with order_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(order, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"TASK_ORDER_CREATED: {order_path}")
    print(f"CURRENT_STAGE={args.entry}")
    print("ESTIMATE_REQUIRED_BEFORE_START=true")
    print(f"NEXT_ACTION={LABELS[args.entry]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
