#!/usr/bin/env python3
"""Verify that a downloaded workflow Skill package is internally complete."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path


LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
# Require another separator after the Windows drive root. This avoids treating
# regex fragments such as ``name:\s`` as machine-specific paths.
WINDOWS_ABSOLUTE_PATH_RE = re.compile(
    r"(?i)(?<![a-z0-9])[a-z]:[\\/][^\s\"'<>]+[\\/]"
)
POSIX_HOME_MARKERS = ("/" + "users" + "/", "/" + "home" + "/")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        default=Path(__file__).resolve().parent.parent,
        type=Path,
        help="Skill package root; defaults to the package containing this script",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = root / "distribution-manifest.json"
    errors: list[str] = []

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"DISTRIBUTION_FAIL: cannot read {manifest_path}: {exc}", file=sys.stderr)
        return 1

    if manifest.get("schema_version") != 1:
        errors.append("distribution-manifest.json schema_version must be 1")
    if manifest.get("package_name") != "digital-human-complete-workflow":
        errors.append("distribution manifest package_name mismatch")

    try:
        default_profile = json.loads(
            (root / "assets" / "workflow-profile.example.json").read_text(encoding="utf-8")
        )
        avatar_binding = default_profile["stage_skills"]["avatar"]
        if avatar_binding.get("skill") != "digital-human-avatar-musetalk":
            errors.append("default avatar stage must use digital-human-avatar-musetalk")
        bundled_path = avatar_binding.get("bundled_path")
        if not isinstance(bundled_path, str) or not (root / bundled_path / "SKILL.md").is_file():
            errors.append("default avatar stage bundled_path is missing or invalid")
    except (OSError, UnicodeError, KeyError, TypeError, json.JSONDecodeError) as exc:
        errors.append(f"cannot validate default avatar stage binding: {exc}")

    required = manifest.get("required_internal_files")
    if not isinstance(required, list) or not required:
        errors.append("required_internal_files must be a non-empty list")
        required = []
    for relative in required:
        if not isinstance(relative, str) or not relative:
            errors.append(f"invalid required file entry: {relative!r}")
            continue
        path = root / relative
        if not path.is_file():
            errors.append(f"missing required file: {relative}")

    for path in root.rglob("*"):
        if path.is_dir() and path.name == "__pycache__":
            errors.append(f"cache directory must not ship: {path.relative_to(root)}")
        if path.is_file() and path.suffix.lower() == ".pyc":
            errors.append(f"compiled cache must not ship: {path.relative_to(root)}")

    forbidden_suffixes = set(manifest.get("forbidden_payload_suffixes", []))
    allowed_payloads = set(manifest.get("allowed_payload_files", []))
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if path.suffix.lower() in forbidden_suffixes and relative not in allowed_payloads:
            errors.append(f"sensitive or non-redistributable payload found: {relative}")

    for path in root.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {path.relative_to(root)}: {exc}")

    for path in root.rglob("*.py"):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as exc:
            errors.append(f"invalid Python {path.relative_to(root)}: {exc}")

    for path in root.rglob("*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read Markdown {path.relative_to(root)}: {exc}")
            continue
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip().strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if target and not (path.parent / target).resolve().exists():
                errors.append(
                    f"broken local link in {path.relative_to(root)}: {raw_target}"
                )

    scan_suffixes = {".md", ".json", ".yaml", ".yml", ".py", ".ps1"}
    allowed_absolute = set(manifest.get("allowed_absolute_path_files", []))
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in scan_suffixes:
            continue
        relative = path.relative_to(root).as_posix()
        if relative in allowed_absolute:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        text_without_urls = re.sub(r"https?://[^\s)>]+", "", text)
        lowered = text_without_urls.lower()
        has_absolute_path = WINDOWS_ABSOLUTE_PATH_RE.search(text_without_urls) or any(
            marker in lowered for marker in POSIX_HOME_MARKERS
        )
        if has_absolute_path:
            errors.append(f"machine-specific absolute path found: {relative}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"DISTRIBUTION_FAIL: {len(errors)} error(s)", file=sys.stderr)
        return 1

    scope = manifest.get("bundle_scope", "unknown")
    runtime_included = bool(manifest.get("end_to_end_runtime_included"))
    print(f"DISTRIBUTION_OK: internal package complete; scope={scope}")
    print(f"END_TO_END_RUNTIME_INCLUDED={str(runtime_included).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
