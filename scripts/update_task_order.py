#!/usr/bin/env python3
"""安全推进任务订单，并验证每个阶段的真实交接文件。"""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

STAGES = ("rewrite", "voice", "avatar", "packaging")
LABELS = {"rewrite": "开始二创", "voice": "开始数字人音频", "avatar": "开始数字人画面", "packaging": "开始剪辑包装"}
HANDOFF_STAGE = {"rewrite": "script", "voice": "audio", "avatar": "avatar", "packaging": "packaging"}

def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): value.update(block)
    return value.hexdigest()

def valid_sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)

def resolve_artifact(handoff: Path, value: object) -> Path:
    if not isinstance(value, str) or not value.strip(): raise ValueError("交接文件中存在空的产物路径")
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (handoff.parent / path).resolve()

def verify_file_item(handoff: Path, item: object, label: str) -> Path:
    if not isinstance(item, dict): raise ValueError(f"{label}格式不正确")
    path = resolve_artifact(handoff, item.get("path"))
    if not path.is_file() or path.stat().st_size <= 0: raise ValueError(f"{label}不存在或为空：{path}")
    declared = item.get("sha256")
    if not valid_sha(declared) or sha256(path).lower() != str(declared).lower(): raise ValueError(f"{label}的 SHA-256 与文件不一致")
    return path

def read_json(path: Path, label: str) -> dict:
    try: payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc: raise ValueError(f"{label}无法读取：{exc}") from exc
    if not isinstance(payload, dict): raise ValueError(f"{label}根节点必须是对象")
    return payload

def verify_handoff(order: dict, stage: str, handoff: Path) -> None:
    payload = read_json(handoff, "交接文件")
    if payload.get("schema_version") != 1: raise ValueError("交接文件 schema_version 必须为 1")
    if payload.get("run_id") != order.get("order_id"): raise ValueError("交接文件不属于当前任务，禁止跨任务串用")
    if payload.get("stage") != HANDOFF_STAGE[stage]: raise ValueError(f"当前阶段需要 {HANDOFF_STAGE[stage]} 交接文件")
    binding = order.get("stage_skills", {}).get(stage, {})
    expected_skill = binding.get("skill") if isinstance(binding, dict) else None
    stage_skill = payload.get("stage_skill")
    if not isinstance(stage_skill, dict) or stage_skill.get("name") != expected_skill: raise ValueError("交接文件的阶段 Skill 与订单绑定不一致")
    expected_status = "qa_passed" if stage == "packaging" else "approved"
    if payload.get("status") != expected_status: raise ValueError(f"交接状态必须是 {expected_status}")
    outputs = payload.get("outputs")
    if not isinstance(outputs, list) or not outputs: raise ValueError("交接文件必须列出真实输出")
    roles: set[str] = set()
    for index, item in enumerate(outputs):
        verify_file_item(handoff, item, f"第 {index + 1} 个输出")
        if isinstance(item, dict) and isinstance(item.get("role"), str): roles.add(item["role"])
    if "primary" not in roles: raise ValueError("交接文件缺少 primary 主产物")
    if payload.get("native_manifest") is not None: verify_file_item(handoff, payload["native_manifest"], "阶段原生清单")
    if stage != "packaging":
        approval = payload.get("approval")
        if not isinstance(approval, dict) or approval.get("required") is not True: raise ValueError("进入下一阶段前必须记录用户确认")
        if not approval.get("approved_by") or not approval.get("approval_text"): raise ValueError("用户确认记录缺少确认人或确认原话")
    if stage != order.get("entry_stage"):
        inputs = payload.get("inputs")
        if not isinstance(inputs, list) or not inputs: raise ValueError("交接文件缺少上游输入绑定")
        previous = STAGES[STAGES.index(stage) - 1]
        previous_record = order.get("stages", {}).get(previous, {}).get("output_handoff")
        if not isinstance(previous_record, dict): raise ValueError("订单没有可验证的上游交接记录")
        previous_path = (Path(order["_order_path"]).parent / previous_record["path"]).resolve()
        matched = False
        for item in inputs:
            try: input_path = verify_file_item(handoff, item, "上游输入")
            except ValueError: continue
            if input_path == previous_path and str(item.get("sha256", "")).lower() == str(previous_record.get("sha256", "")).lower(): matched = True
        if not matched: raise ValueError("交接文件没有绑定订单中已确认的上游交接文件")

def load_order(path: Path) -> dict:
    order = read_json(path, "任务订单")
    if order.get("schema_version") != 1 or not isinstance(order.get("stages"), dict): raise ValueError("任务订单结构不正确")
    order["_order_path"] = str(path)
    return order

def save_order(path: Path, order: dict) -> None:
    clean = dict(order); clean.pop("_order_path", None)
    temp = path.with_name(path.name + ".tmp")
    if temp.exists(): raise ValueError(f"存在未清理的临时文件：{temp}")
    temp.write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)

def timestamp() -> str: return datetime.now(timezone.utc).isoformat()
def add_history(order: dict, event: str, stage: str, **details: object) -> None:
    item = {"at": timestamp(), "event": event, "stage": stage, **details}; order.setdefault("history", []).append(item); order["updated_at"] = item["at"]
def require_current(order: dict, stage: str) -> dict:
    if order.get("current_stage") != stage: raise ValueError(f"当前阶段是 {order.get('current_stage')}，不能操作 {stage}")
    entry = order["stages"].get(stage)
    if not isinstance(entry, dict): raise ValueError(f"任务订单缺少阶段：{stage}")
    return entry

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"): sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("order", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start"); start.add_argument("--stage", choices=STAGES, required=True); start.add_argument("--estimate-low", type=float, required=True); start.add_argument("--estimate-high", type=float, required=True); start.add_argument("--basis", required=True)
    complete = commands.add_parser("complete"); complete.add_argument("--stage", choices=STAGES, required=True); complete.add_argument("--handoff", type=Path, required=True)
    fail = commands.add_parser("fail"); fail.add_argument("--stage", choices=STAGES, required=True); fail.add_argument("--reason", required=True); fail.add_argument("--retry-low", type=float, required=True); fail.add_argument("--retry-high", type=float, required=True); fail.add_argument("--basis", required=True)
    update = commands.add_parser("needs-update"); update.add_argument("--from-stage", choices=STAGES, required=True); update.add_argument("--reason", required=True)
    extend = commands.add_parser("extend"); extend.add_argument("--target", choices=STAGES, required=True)
    args = parser.parse_args(); order_path = args.order.expanduser().resolve()
    try:
        order = load_order(order_path)
        if args.command == "start":
            entry = require_current(order, args.stage)
            if entry.get("state") not in {"ready", "failed", "needs_update"}: raise ValueError("当前阶段尚不能开始")
            if args.estimate_low <= 0 or args.estimate_high < args.estimate_low: raise ValueError("预计时间必须满足 0 < 最短时间 <= 最长时间")
            entry["estimate"] = {"status": "shown_before_start", "low_minutes": args.estimate_low, "high_minutes": args.estimate_high, "basis": args.basis, "calculated_at": timestamp()}; entry["state"] = "running"; entry["failure"] = None
            order["status"] = "running"; order["next_action"] = {"type": "run_stage", "stage": args.stage, "label": LABELS[args.stage]}
            add_history(order, "stage_started", args.stage, estimate_low=args.estimate_low, estimate_high=args.estimate_high, basis=args.basis)
            print(f"阶段已开始：{args.stage}；预计 {args.estimate_low:g}-{args.estimate_high:g} 分钟")
        elif args.command == "complete":
            entry = require_current(order, args.stage)
            if entry.get("state") != "running": raise ValueError("阶段必须先开始，才能标记完成")
            handoff = args.handoff.expanduser().resolve()
            if not handoff.is_file(): raise ValueError(f"交接文件不存在：{handoff}")
            verify_handoff(order, args.stage, handoff)
            record = {"path": os.path.relpath(handoff, order_path.parent), "sha256": sha256(handoff), "historical": False}; entry["state"] = "completed"; entry["output_handoff"] = record
            index = STAGES.index(args.stage); following = STAGES[index + 1] if index < STAGES.index(order["target_stage"]) else None
            if following is None:
                order["status"] = "completed"; order["current_stage"] = None; order["next_action"] = {"type": "done", "stage": None, "label": "任务完成"}; add_history(order, "order_completed", args.stage, handoff_sha256=record["sha256"]); print("任务已完成并通过交接校验。")
            else:
                order["stages"][following]["state"] = "ready"; order["stages"][following]["input_handoff"] = dict(record); order["status"] = "ready"; order["current_stage"] = following; order["next_action"] = {"type": "estimate_and_start", "stage": following, "label": LABELS[following]}; add_history(order, "stage_completed", args.stage, handoff_sha256=record["sha256"], next_stage=following); print(f"下一阶段：{following}。开始前请先显示预计时间。")
        elif args.command == "fail":
            entry = require_current(order, args.stage)
            if args.retry_low <= 0 or args.retry_high < args.retry_low: raise ValueError("重试预计时间不正确")
            entry["state"] = "failed"; entry["failure"] = {"reason": args.reason, "recorded_at": timestamp(), "retry_estimate": {"low_minutes": args.retry_low, "high_minutes": args.retry_high, "basis": args.basis}}; order["status"] = "failed"; order["next_action"] = {"type": "review_failure_and_retry", "stage": args.stage, "label": f"查看失败原因并重试{LABELS[args.stage][2:]}"}; add_history(order, "stage_failed", args.stage, reason=args.reason); print(f"阶段未完成：{args.reason}。预计重试 {args.retry_low:g}-{args.retry_high:g} 分钟。")
        elif args.command == "needs-update":
            if STAGES.index(args.from_stage) < STAGES.index(order["entry_stage"]): raise ValueError("不能从本订单入口之前的阶段发起修改")
            if STAGES.index(args.from_stage) > STAGES.index(order["target_stage"]): raise ValueError("修改阶段超出本订单范围")
            for stage in STAGES[STAGES.index(args.from_stage):STAGES.index(order["target_stage"]) + 1]:
                entry = order["stages"][stage]
                if isinstance(entry.get("output_handoff"), dict): entry["output_handoff"]["historical"] = True
                entry["state"] = "needs_update"; entry["failure"] = None
            order["status"] = "needs_update"; order["current_stage"] = args.from_stage; order["next_action"] = {"type": "estimate_and_start", "stage": args.from_stage, "label": f"更新{LABELS[args.from_stage][2:]}"}; add_history(order, "version_update_required", args.from_stage, reason=args.reason); print(f"将从 {args.from_stage} 重新制作；旧产物只作历史记录。")
        else:
            old = order["target_stage"]
            if STAGES.index(args.target) <= STAGES.index(old): raise ValueError("延长后的目标必须位于当前目标之后")
            previous = order["stages"][old]; handoff = previous.get("output_handoff")
            if previous.get("state") != "completed" or not isinstance(handoff, dict): raise ValueError("当前目标尚未完成并通过交接校验")
            first = STAGES[STAGES.index(old) + 1]
            for stage in STAGES[STAGES.index(old) + 1:STAGES.index(args.target) + 1]:
                entry = order["stages"][stage]; entry["state"] = "ready" if stage == first else "queued"; entry["input_handoff"] = dict(handoff) if stage == first else None; entry["output_handoff"] = None; entry["estimate"] = {"status": "required_before_start", "low_minutes": None, "high_minutes": None, "basis": None, "calculated_at": None}; entry["failure"] = None
            order["target_stage"] = args.target; order["status"] = "ready"; order["current_stage"] = first; order["next_action"] = {"type": "estimate_and_start", "stage": first, "label": LABELS[first]}; add_history(order, "order_extended", first, previous_target=old, new_target=args.target); print(f"订单已延长到 {args.target}；下一阶段为 {first}。")
        save_order(order_path, order); return 0
    except (KeyError, OSError, ValueError) as exc:
        print(f"操作未完成：{exc}", file=sys.stderr); return 2

if __name__ == "__main__": raise SystemExit(main())
