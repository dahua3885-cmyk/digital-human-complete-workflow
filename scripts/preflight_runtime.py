#!/usr/bin/env python3
"""Check stage Skills and provider/runtime prerequisites before a workflow run."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
from pathlib import Path


STAGES = ("rewrite", "voice", "avatar", "packaging")
SKILL_NAME_RE = re.compile(r"^name:\s*([a-z0-9]+(?:-[a-z0-9]+)*)\s*$", re.MULTILINE)


def resolve_config_path(config_dir: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (config_dir / path).resolve()


def discover_skill_root(name: str, script_root: Path) -> Path | None:
    candidates = [script_root.parent / name]
    codex_home = os.getenv("CODEX_HOME")
    if codex_home:
        candidates.append(Path(codex_home).expanduser() / "skills" / name)
    candidates.append(Path.home() / ".codex" / "skills" / name)
    for candidate in candidates:
        resolved = candidate.resolve()
        if (resolved / "SKILL.md").is_file():
            return resolved
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config_dir = config_path.parent
    installed_skill_root = Path(__file__).resolve().parents[1]
    errors: list[str] = []
    ready: list[str] = []

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"RUNTIME_BLOCKED: cannot read config: {exc}", file=sys.stderr)
        return 1

    if config.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    enabled = config.get("enabled_stages")
    if not isinstance(enabled, list) or not enabled:
        errors.append("enabled_stages must be a non-empty list")
        enabled = []
    unknown = sorted(set(enabled) - set(STAGES))
    if unknown:
        errors.append(f"unknown enabled stage(s): {', '.join(unknown)}")

    stages = config.get("stages")
    if not isinstance(stages, dict):
        errors.append("stages must be an object")
        stages = {}

    for stage in enabled:
        entry = stages.get(stage)
        prefix = f"stages.{stage}"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        name = entry.get("skill_name")
        root_value = entry.get("skill_root")
        if not isinstance(name, str) or not name or "replace-" in name:
            errors.append(f"{prefix}.skill_name is not configured")
        if isinstance(root_value, str) and root_value and "replace-" not in root_value:
            skill_root = resolve_config_path(config_dir, root_value)
        elif isinstance(name, str) and name and "replace-" not in name:
            skill_root = discover_skill_root(name, installed_skill_root)
            if skill_root is None:
                errors.append(f"{prefix}: Skill {name!r} is not installed or discoverable")
                continue
        else:
            errors.append(f"{prefix}.skill_root is not configured")
            continue
        skill_md = skill_root / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{prefix}: missing SKILL.md at {skill_root}")
        else:
            try:
                match = SKILL_NAME_RE.search(skill_md.read_text(encoding="utf-8"))
            except (OSError, UnicodeError) as exc:
                errors.append(f"{prefix}: cannot read SKILL.md: {exc}")
                match = None
            if match and isinstance(name, str) and match.group(1) != name:
                errors.append(
                    f"{prefix}: configured name {name!r} does not match {match.group(1)!r}"
                )
            elif not match:
                errors.append(f"{prefix}: SKILL.md has no valid name")

        if entry.get("adapter_contract_version") != 1:
            errors.append(f"{prefix}.adapter_contract_version must be 1")
        if entry.get("readiness_attested") is not True:
            errors.append(f"{prefix}.readiness_attested must be true after provider setup")

        checks = entry.get("checks")
        if not isinstance(checks, list):
            errors.append(f"{prefix}.checks must be a list")
            checks = []
        for index, check in enumerate(checks):
            label = f"{prefix}.checks[{index}]"
            if not isinstance(check, dict):
                errors.append(f"{label} must be an object")
                continue
            check_type = check.get("type")
            value = check.get("value")
            if not isinstance(value, str) or not value or "replace-" in value:
                errors.append(f"{label}.value is not configured")
                continue
            if check_type == "command":
                explicit = Path(value).expanduser()
                found = explicit.is_file() if explicit.is_absolute() else shutil.which(value)
                if not found:
                    errors.append(f"{label}: command not found: {value}")
            elif check_type == "path":
                if not resolve_config_path(config_dir, value).exists():
                    errors.append(f"{label}: path not found: {value}")
            elif check_type == "env":
                if not os.getenv(value):
                    errors.append(f"{label}: environment variable is not set: {value}")
            elif check_type == "python_module":
                if importlib.util.find_spec(value) is None:
                    errors.append(f"{label}: Python module not found: {value}")
            else:
                errors.append(f"{label}.type must be command, path, env, or python_module")
        ready.append(stage)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"RUNTIME_BLOCKED: {len(errors)} error(s)", file=sys.stderr)
        return 1

    print(f"END_TO_END_READY: {', '.join(ready)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
