#!/usr/bin/env python3
"""Behavioral checks for bundled avatar-stage installation, migration, and runtime planning."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
AVATAR = ROOT / "bundled-stages" / "digital-human-avatar-musetalk"


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        command,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )


def main() -> int:
    profile = json.loads((ROOT / "assets" / "workflow-profile.example.json").read_text(encoding="utf-8"))
    if profile["stage_skills"]["avatar"]["skill"] != "digital-human-avatar-musetalk":
        raise AssertionError("public workflow still uses an example avatar binding")

    with tempfile.TemporaryDirectory(prefix="avatar-stage-test ") as temporary:
        temporary_root = Path(temporary)
        skills_dir = temporary_root / "skills"
        skills_dir.mkdir()
        installed = run(
            [sys.executable, str(SCRIPTS / "install_bundled_stage_skills.py"), "--skills-dir", str(skills_dir)]
        )
        payload = json.loads(installed.stdout)
        installed_skill = skills_dir / "digital-human-avatar-musetalk"
        if payload.get("status") != "installed" or not (installed_skill / "SKILL.md").is_file():
            raise AssertionError("bundled avatar Skill was not installed")

        legacy = temporary_root / "workflow-profile.json"
        legacy_payload = json.loads((ROOT / "assets" / "workflow-profile.example.json").read_text(encoding="utf-8"))
        legacy_payload["stage_skills"]["avatar"] = {"skill": "your-digital-human-video-skill"}
        legacy.write_text(json.dumps(legacy_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        run([sys.executable, str(SCRIPTS / "migrate_stage_bindings.py"), str(legacy)])
        migrated = json.loads(legacy.read_text(encoding="utf-8"))
        if migrated["stage_skills"]["avatar"]["skill"] != "digital-human-avatar-musetalk":
            raise AssertionError("legacy avatar binding was not migrated")

        setup = installed_skill / "scripts" / "setup_runtime.py"
        plan = run([sys.executable, str(setup), "--runtime-root", str(temporary_root / "runtime"), "--dry-run"])
        plan_payload = json.loads(plan.stdout)
        if plan_payload.get("commit") != "0a89dec45a0192b824e3cf4daf96c239440c5ed8":
            raise AssertionError("avatar runtime is not pinned to the reviewed official commit")

        check_runtime = installed_skill / "scripts" / "check_runtime.py"
        missing = run(
            [sys.executable, str(check_runtime), "--config", str(temporary_root / "missing.json"), "--json"],
            check=False,
        )
        missing_payload = json.loads(missing.stdout)
        if missing.returncode == 0 or missing_payload.get("ready") is not False:
            raise AssertionError("missing avatar runtime was incorrectly accepted")
        if not all(isinstance(item, str) and item for item in missing_payload.get("problems_zh", [])):
            raise AssertionError("missing runtime did not return customer-readable Chinese reasons")

    print("AVATAR_STAGE_TEST_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
