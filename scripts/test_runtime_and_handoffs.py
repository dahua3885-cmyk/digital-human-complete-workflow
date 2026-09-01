#!/usr/bin/env python3
"""Regression tests for false-ready, consent, and handoff integrity bugs."""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def digest(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"})
def write_json(path: Path, payload: object) -> None: path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def base_order(path: Path, stage: str, skill: str, run_id: str) -> dict:
    stages = {name: {"state": "skipped", "input_handoff": None, "output_handoff": None} for name in ("rewrite", "voice", "avatar", "packaging")}
    stages[stage]["state"] = "running"
    return {"schema_version": 1, "order_id": run_id, "entry_stage": stage, "target_stage": stage, "status": "running", "current_stage": stage, "stage_skills": {stage: {"skill": skill}}, "stages": stages, "history": [], "_path": str(path)}

def main() -> int:
    with tempfile.TemporaryDirectory(prefix="workflow-integrity-") as temporary:
        root = Path(temporary)
        false_ready = root / "runtime.json"
        write_json(false_ready, {"schema_version": 1, "enabled_stages": ["voice"], "stages": {"voice": {"skill_name": "replace-voice", "adapter_contract_version": 1, "readiness_attested": True, "checks": []}}})
        checked = run(ROOT / "scripts" / "preflight_runtime.py", str(false_ready), "--json")
        if checked.returncode == 0 or json.loads(checked.stdout).get("ready") is not False: raise AssertionError("placeholder/handwritten ready flag was accepted")

        workspace = root / "workspace"
        initialized = run(ROOT / "scripts" / "init_user_workspace.py", str(workspace))
        if initialized.returncode != 0: raise AssertionError(initialized.stderr)
        invalid = run(ROOT / "scripts" / "save_consent_record.py", str(workspace), str(workspace / ".private" / "consent" / "consent-record.json"))
        if invalid.returncode == 0 or "合法" not in invalid.stderr: raise AssertionError("default consent example was accepted")
        consent = json.loads((workspace / ".private" / "consent" / "consent-record.json").read_text(encoding="utf-8"))
        consent["lawful_use_confirmed"] = True
        consent["subject"] = {"name": "测试本人", "relationship": "self"}
        consent["permissions"].update({"voice_clone": True, "likeness_lip_sync": True, "video_editing": True, "publication": True, "platforms": ["测试平台"], "territory": "中国大陆"})
        consent["notice"].update({"purpose": "测试本人数字人工作流", "retention": "项目结束后30天", "rights_and_risks_explained": True})
        consent["evidence"].update({"confirmation_text": "本人同意按上述范围制作", "confirmed_at": "2026-09-01T00:00:00Z", "confirmed": True})
        consent["revocation"].update({"method": "删除本地授权文件", "contact": "本人"})
        consent_path = root / "valid-consent.json"; write_json(consent_path, consent)
        valid = run(ROOT / "scripts" / "save_consent_record.py", str(workspace), str(consent_path))
        if valid.returncode != 0 or "已在本机建立" not in valid.stdout: raise AssertionError(valid.stderr)

        order_path = root / "task-order.json"; order = base_order(order_path, "packaging", "digital-human-packaging-fixed", "order-a"); write_json(order_path, order)
        empty = root / "empty.json"; write_json(empty, {})
        rejected = run(ROOT / "scripts" / "update_task_order.py", str(order_path), "complete", "--stage", "packaging", "--handoff", str(empty))
        if rejected.returncode == 0: raise AssertionError("empty packaging JSON completed an order")

        artifact = root / "result.mp4"; artifact.write_bytes(b"public-test-artifact")
        wrong = root / "wrong-task.json"
        write_json(wrong, {"schema_version": 1, "run_id": "another-order", "stage": "packaging", "status": "qa_passed", "stage_skill": {"name": "digital-human-packaging-fixed", "version": "1"}, "outputs": [{"role": "primary", "path": str(artifact), "sha256": digest(artifact)}]})
        rejected = run(ROOT / "scripts" / "update_task_order.py", str(order_path), "complete", "--stage", "packaging", "--handoff", str(wrong))
        if rejected.returncode == 0 or "不属于当前任务" not in rejected.stderr: raise AssertionError("cross-task handoff was accepted")

        valid_handoff = root / "valid-packaging.json"
        write_json(valid_handoff, {"schema_version": 1, "run_id": "order-a", "stage": "packaging", "status": "qa_passed", "stage_skill": {"name": "digital-human-packaging-fixed", "version": "1"}, "outputs": [{"role": "primary", "path": str(artifact), "sha256": digest(artifact)}]})
        accepted = run(ROOT / "scripts" / "update_task_order.py", str(order_path), "complete", "--stage", "packaging", "--handoff", str(valid_handoff))
        if accepted.returncode != 0: raise AssertionError(accepted.stderr)

    print("RUNTIME_AND_HANDOFF_TEST_OK"); return 0

if __name__ == "__main__": raise SystemExit(main())
