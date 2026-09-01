#!/usr/bin/env python3
"""Behavior tests for customer-facing Chinese status rendering."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RAW_STATUSES = (
    "ready",
    "pending",
    "needs_recalibration",
    "needs_review",
    "not_selected",
    "blocked",
)


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
    )


def main() -> int:
    example = ROOT / "assets" / "asset-center.example.json"
    rendered = run(str(ROOT / "scripts" / "render_customer_asset_status.py"), str(example))
    if rendered.returncode != 0:
        raise AssertionError(rendered.stderr)
    for raw in RAW_STATUSES:
        if raw in rendered.stdout:
            raise AssertionError(f"raw internal status leaked to customer output: {raw}")
    for phrase in (
        "创作者资料：尚未建立",
        "数字人音频：首次使用时准备",
        "数字人形象：首次使用时准备",
        "剪辑包装：使用时自动准备",
    ):
        if phrase not in rendered.stdout:
            raise AssertionError(f"missing customer-facing phrase: {phrase}")

    with tempfile.TemporaryDirectory(prefix="资料提交后状态-") as temp:
        submitted_path = Path(temp) / "asset-center.json"
        submitted = json.loads(example.read_text(encoding="utf-8"))
        submitted["profiles"]["creator"]["status"] = "ready"
        submitted_path.write_text(
            json.dumps(submitted, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        after_submission = run(
            str(ROOT / "scripts" / "render_customer_asset_status.py"),
            str(submitted_path),
        )
        if after_submission.returncode != 0:
            raise AssertionError(after_submission.stderr)
        if "创作者资料：已建立" not in after_submission.stdout:
            raise AssertionError("submitted creator profile must render as 已建立")
        for raw in RAW_STATUSES:
            if raw in after_submission.stdout:
                raise AssertionError(
                    f"raw internal status leaked after profile submission: {raw}"
                )

    with tempfile.TemporaryDirectory(prefix="数字人状态测试-") as temp:
        workspace = Path(temp) / "含 空格工作区"
        initialized = run(
            str(ROOT / "scripts" / "init_user_workspace.py"),
            str(workspace),
            "--modules",
            "all",
            "--creator-profile",
            "quick",
        )
        if initialized.returncode != 0:
            raise AssertionError(initialized.stderr or initialized.stdout)
        asset_center = json.loads(
            (workspace / "profiles" / "asset-center.json").read_text(encoding="utf-8")
        )
        onboarding = json.loads(
            (workspace / "profiles" / "onboarding-status.json").read_text(
                encoding="utf-8"
            )
        )
        if asset_center["profiles"]["packaging"]["status"] != "pending":
            raise AssertionError("packaging runtime must be prepared on first use")
        if onboarding["modules"]["packaging"]["status"] != "pending":
            raise AssertionError("packaging onboarding must be prepared on first use")

    print("CUSTOMER_ASSET_STATUS_TEST_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
