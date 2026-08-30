#!/usr/bin/env python3
"""Start, complete, fail, or mark version updates in a task order."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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
EXPECTED_HANDOFF_STAGE = {
    "rewrite": "script",
    "voice": "audio",
    "avatar": "avatar",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_order(path: Path) -> dict:
    try:
        order = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read task order: {exc}") from exc
    if not isinstance(order, dict) or order.get("schema_version") != 1:
        raise ValueError("task order schema_version must be 1")
    if not isinstance(order.get("stages"), dict):
        raise ValueError("task order stages must be an object")
    return order


def save_order(path: Path, order: dict) -> None:
    temp = path.with_name(path.name + ".tmp")
    if temp.exists():
        raise ValueError(f"temporary file already exists: {temp}")
    with temp.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(order, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temp, path)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_history(order: dict, event: str, stage: str, **details: object) -> None:
    item = {"at": timestamp(), "event": event, "stage": stage}
    item.update(details)
    order.setdefault("history", []).append(item)
    order["updated_at"] = item["at"]


def require_current(order: dict, stage: str) -> dict:
    if order.get("current_stage") != stage:
        raise ValueError(
            f"current stage is {order.get('current_stage')!r}; cannot update {stage!r}"
        )
    entry = order["stages"].get(stage)
    if not isinstance(entry, dict):
        raise ValueError(f"missing stage entry: {stage}")
    return entry


def next_stage(order: dict, stage: str) -> str | None:
    target_index = STAGES.index(order["target_stage"])
    index = STAGES.index(stage)
    return STAGES[index + 1] if index < target_index else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("order", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start")
    start.add_argument("--stage", choices=STAGES, required=True)
    start.add_argument("--estimate-low", type=float, required=True)
    start.add_argument("--estimate-high", type=float, required=True)
    start.add_argument("--basis", required=True)

    complete = subparsers.add_parser("complete")
    complete.add_argument("--stage", choices=STAGES, required=True)
    complete.add_argument("--handoff", type=Path, required=True)

    fail = subparsers.add_parser("fail")
    fail.add_argument("--stage", choices=STAGES, required=True)
    fail.add_argument("--reason", required=True)
    fail.add_argument("--retry-low", type=float, required=True)
    fail.add_argument("--retry-high", type=float, required=True)
    fail.add_argument("--basis", required=True)

    update = subparsers.add_parser("needs-update")
    update.add_argument("--from-stage", choices=STAGES, required=True)
    update.add_argument("--reason", required=True)

    extend = subparsers.add_parser("extend")
    extend.add_argument("--target", choices=STAGES, required=True)

    args = parser.parse_args()
    order_path = args.order.expanduser().resolve()
    try:
        order = load_order(order_path)

        if args.command == "start":
            stage_entry = require_current(order, args.stage)
            if stage_entry.get("state") not in {"ready", "failed", "needs_update"}:
                raise ValueError(f"stage {args.stage} is not ready to start")
            if args.estimate_low <= 0 or args.estimate_high < args.estimate_low:
                raise ValueError("estimate must satisfy 0 < low <= high")
            stage_entry["estimate"] = {
                "status": "shown_before_start",
                "low_minutes": args.estimate_low,
                "high_minutes": args.estimate_high,
                "basis": args.basis,
                "calculated_at": timestamp(),
            }
            stage_entry["state"] = "running"
            stage_entry["failure"] = None
            order["status"] = "running"
            order["next_action"] = {
                "type": "run_stage",
                "stage": args.stage,
                "label": LABELS[args.stage],
            }
            add_history(
                order,
                "stage_started",
                args.stage,
                estimate_low=args.estimate_low,
                estimate_high=args.estimate_high,
                basis=args.basis,
            )
            print(
                f"STAGE_STARTED: {args.stage}; estimate={args.estimate_low:g}-{args.estimate_high:g} minutes"
            )

        elif args.command == "complete":
            stage_entry = require_current(order, args.stage)
            if stage_entry.get("state") != "running":
                raise ValueError(f"stage {args.stage} must be running before completion")
            handoff = args.handoff.expanduser().resolve()
            if not handoff.is_file():
                raise ValueError(f"handoff not found: {handoff}")
            try:
                handoff_payload = json.loads(handoff.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"handoff must be valid JSON: {exc}") from exc
            if not isinstance(handoff_payload, dict):
                raise ValueError("handoff root must be an object")
            expected_stage = EXPECTED_HANDOFF_STAGE.get(args.stage)
            if expected_stage is not None:
                if handoff_payload.get("stage") != expected_stage:
                    raise ValueError(
                        f"handoff stage must be {expected_stage!r} for {args.stage!r}"
                    )
                approval = handoff_payload.get("approval")
                if not isinstance(approval, dict):
                    raise ValueError("handoff must contain the required user approval")
                if approval.get("required") is not True:
                    raise ValueError("handoff approval.required must be true")
                if not approval.get("approved_by") or not approval.get("approval_text"):
                    raise ValueError("handoff must record approved_by and approval_text")
                if handoff_payload.get("status") != "approved":
                    raise ValueError("handoff status must be approved")
                outputs = handoff_payload.get("outputs")
                if not isinstance(outputs, list) or not outputs:
                    raise ValueError("handoff must contain at least one output")
                primary = next(
                    (
                        output
                        for output in outputs
                        if isinstance(output, dict) and output.get("role") == "primary"
                    ),
                    None,
                )
                if primary is None:
                    raise ValueError("handoff must contain a primary output")
                artifact_value = primary.get("path")
                declared_sha = primary.get("sha256")
                if not isinstance(artifact_value, str) or not artifact_value:
                    raise ValueError("primary output path is missing")
                artifact = Path(artifact_value).expanduser()
                if not artifact.is_absolute():
                    artifact = (handoff.parent / artifact).resolve()
                if not artifact.is_file():
                    raise ValueError(f"primary output not found: {artifact}")
                if (
                    not isinstance(declared_sha, str)
                    or len(declared_sha) != 64
                    or any(char not in "0123456789abcdefABCDEF" for char in declared_sha)
                ):
                    raise ValueError("primary output sha256 must be 64 hexadecimal characters")
                actual_sha = sha256(artifact)
                if actual_sha.lower() != declared_sha.lower():
                    raise ValueError("primary output sha256 does not match the file")
            record = {
                "path": os.path.relpath(handoff, order_path.parent),
                "sha256": sha256(handoff),
                "historical": False,
            }
            stage_entry["state"] = "completed"
            stage_entry["output_handoff"] = record
            following = next_stage(order, args.stage)
            if following is None:
                order["status"] = "completed"
                order["current_stage"] = None
                order["next_action"] = {"type": "done", "stage": None, "label": "任务完成"}
                add_history(order, "order_completed", args.stage, handoff_sha256=record["sha256"])
                print("ORDER_COMPLETED")
            else:
                next_entry = order["stages"][following]
                next_entry["state"] = "ready"
                next_entry["input_handoff"] = dict(record)
                order["status"] = "ready"
                order["current_stage"] = following
                order["next_action"] = {
                    "type": "estimate_and_start",
                    "stage": following,
                    "label": LABELS[following],
                }
                add_history(
                    order,
                    "stage_completed",
                    args.stage,
                    handoff_sha256=record["sha256"],
                    next_stage=following,
                )
                print(f"NEXT_STAGE={following}")
                print(f"INPUT_HANDOFF={record['path']}")
                print("ESTIMATE_REQUIRED_BEFORE_START=true")

        elif args.command == "fail":
            stage_entry = require_current(order, args.stage)
            if args.retry_low <= 0 or args.retry_high < args.retry_low:
                raise ValueError("retry estimate must satisfy 0 < low <= high")
            stage_entry["state"] = "failed"
            stage_entry["failure"] = {
                "reason": args.reason,
                "recorded_at": timestamp(),
                "retry_estimate": {
                    "low_minutes": args.retry_low,
                    "high_minutes": args.retry_high,
                    "basis": args.basis,
                },
            }
            order["status"] = "failed"
            order["next_action"] = {
                "type": "review_failure_and_retry",
                "stage": args.stage,
                "label": f"查看失败原因并重试{LABELS[args.stage][2:]}",
            }
            add_history(order, "stage_failed", args.stage, reason=args.reason)
            print(f"STAGE_FAILED: {args.stage}; reason={args.reason}")
            print(f"RETRY_ESTIMATE={args.retry_low:g}-{args.retry_high:g} minutes")

        elif args.command == "needs-update":
            from_index = STAGES.index(args.from_stage)
            target_index = STAGES.index(order["target_stage"])
            if from_index > target_index:
                raise ValueError("from-stage is outside this task order")
            for stage in STAGES[from_index : target_index + 1]:
                entry = order["stages"][stage]
                if isinstance(entry.get("output_handoff"), dict):
                    entry["output_handoff"]["historical"] = True
                entry["state"] = "needs_update"
                entry["failure"] = None
            order["status"] = "needs_update"
            order["current_stage"] = args.from_stage
            order["next_action"] = {
                "type": "estimate_and_start",
                "stage": args.from_stage,
                "label": f"更新{LABELS[args.from_stage][2:]}",
            }
            add_history(order, "version_update_required", args.from_stage, reason=args.reason)
            print(f"NEEDS_UPDATE_FROM={args.from_stage}")
            print("HISTORICAL_OUTPUTS_PRESERVED=true")
            print("ESTIMATE_REQUIRED_BEFORE_START=true")

        else:
            old_target = order["target_stage"]
            old_index = STAGES.index(old_target)
            new_index = STAGES.index(args.target)
            if new_index <= old_index:
                raise ValueError("extended target must be after the current target")
            previous = order["stages"][old_target]
            handoff = previous.get("output_handoff")
            if previous.get("state") != "completed" or not isinstance(handoff, dict):
                raise ValueError("current target must be completed with an output handoff before extension")
            first_next = STAGES[old_index + 1]
            for index in range(old_index + 1, new_index + 1):
                stage = STAGES[index]
                entry = order["stages"][stage]
                entry["state"] = "ready" if stage == first_next else "queued"
                entry["input_handoff"] = dict(handoff) if stage == first_next else None
                entry["output_handoff"] = None
                entry["estimate"] = {
                    "status": "required_before_start",
                    "low_minutes": None,
                    "high_minutes": None,
                    "basis": None,
                    "calculated_at": None,
                }
                entry["failure"] = None
            order["target_stage"] = args.target
            order["status"] = "ready"
            order["current_stage"] = first_next
            order["next_action"] = {
                "type": "estimate_and_start",
                "stage": first_next,
                "label": LABELS[first_next],
            }
            add_history(
                order,
                "order_extended",
                first_next,
                previous_target=old_target,
                new_target=args.target,
                input_handoff_sha256=handoff.get("sha256"),
            )
            print(f"ORDER_EXTENDED_TO={args.target}")
            print(f"NEXT_STAGE={first_next}")
            print(f"INPUT_HANDOFF={handoff.get('path')}")
            print("ESTIMATE_REQUIRED_BEFORE_START=true")

        save_order(order_path, order)
        return 0
    except (KeyError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
