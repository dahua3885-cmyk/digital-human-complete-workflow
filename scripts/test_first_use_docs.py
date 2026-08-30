#!/usr/bin/env python3
"""Cross-platform behavioral checks for first-use document delivery."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
PREPARE = SKILL_ROOT / "scripts" / "prepare_first_use_docs.py"
DOCUMENTS = ("数字人完整流程.md", "开始使用前请先填写.md")


def run_prepare(workspace: Path) -> dict[str, str]:
    completed = subprocess.run(
        [sys.executable, str(PREPARE), str(workspace), "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    result = json.loads(completed.stdout)
    if result.get("status") != "DOCS_READY":
        raise AssertionError(f"unexpected status: {result!r}")
    return result


def assert_inside(path: Path, parent: Path) -> None:
    path.resolve().relative_to(parent.resolve())


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="digital-human-首次启用 空格 ") as temporary:
        workspace = Path(temporary)
        first = run_prepare(workspace)

        manual = Path(first["manual_path"])
        profile = Path(first["profile_path"])
        for copied, name in zip((manual, profile), DOCUMENTS, strict=True):
            assert_inside(copied, workspace)
            if copied.read_bytes() != (SKILL_ROOT / name).read_bytes():
                raise AssertionError(f"copied content mismatch: {name}")

        welcome = first["welcome_markdown"]
        if ".codex/skills" in welcome.replace("\\", "/").lower():
            raise AssertionError("welcome must not link to the Skill installation directory")
        if "https://github.com/dahua3885-cmyk/digital-human-complete-workflow/blob/main/" not in welcome:
            raise AssertionError("public online documentation fallback is missing")

        marker = "\n用户填写保护测试：不得覆盖。\n"
        profile.write_text(profile.read_text(encoding="utf-8") + marker, encoding="utf-8")
        second = run_prepare(workspace)
        second_profile = Path(second["profile_path"])
        if second_profile == profile:
            raise AssertionError("a modified user copy was overwritten or reused")
        if marker.strip() not in profile.read_text(encoding="utf-8"):
            raise AssertionError("the modified user copy was not preserved")
        if second_profile.read_bytes() != (SKILL_ROOT / DOCUMENTS[1]).read_bytes():
            raise AssertionError("fresh profile copy does not match the packaged source")

    print("FIRST_USE_DOCS_TEST_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
