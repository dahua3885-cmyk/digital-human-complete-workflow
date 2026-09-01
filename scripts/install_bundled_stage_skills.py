#!/usr/bin/env python3
"""Install bundled public stage Skills beside the complete-workflow Skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


BUNDLED = (
    "digital-human-rewrite-generic",
    "digital-human-voice-chatterbox",
    "digital-human-avatar-musetalk",
    "digital-human-packaging-fixed",
)
MARKER = ".managed-by-digital-human-complete-workflow.json"


def tree_hash(root: Path, *, source_template: bool = False) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if source_template and relative == "STAGE.md":
            relative = "SKILL.md"
        if relative == MARKER or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skills-dir",
        type=Path,
        help="Override the Codex Skills directory; defaults to the parent of this installed Skill",
    )
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    source_root = skill_root / "bundled-stages"
    skills_dir = args.skills_dir.expanduser().resolve() if args.skills_dir else skill_root.parent
    installed: list[dict[str, str]] = []
    for name in BUNDLED:
        source = source_root / name
        destination = skills_dir / name
        if not (source / "STAGE.md").is_file():
            print(f"内置阶段 Skill 缺失：{name}", file=sys.stderr)
            return 2
        source_hash = tree_hash(source, source_template=True)
        marker = destination / MARKER
        if destination.exists() and not marker.is_file():
            print(
                f"无法安装内置阶段 Skill：{destination} 已存在且不是本流程管理的副本。",
                file=sys.stderr,
            )
            return 2
        temporary = skills_dir / f".{name}.installing-{os.getpid()}"
        backup = skills_dir / f".{name}.backup-{os.getpid()}"
        if temporary.exists() or backup.exists():
            print(f"检测到未清理的安装临时目录，暂时不能更新：{name}", file=sys.stderr)
            return 2
        shutil.copytree(source, temporary)
        (temporary / "STAGE.md").replace(temporary / "SKILL.md")
        (temporary / MARKER).write_text(
            json.dumps(
                {
                    "manager": "digital-human-complete-workflow",
                    "source_hash": source_hash,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if tree_hash(temporary) != source_hash:
            shutil.rmtree(temporary)
            print(f"内置阶段 Skill 安装后校验失败：{name}", file=sys.stderr)
            return 2
        try:
            if destination.exists():
                os.replace(destination, backup)
            os.replace(temporary, destination)
            if backup.exists():
                shutil.rmtree(backup)
        except OSError as exc:
            if not destination.exists() and backup.exists():
                os.replace(backup, destination)
            if temporary.exists():
                shutil.rmtree(temporary)
            print(f"内置阶段 Skill 更新未完成：{name}：{exc}", file=sys.stderr)
            return 2
        installed.append({"name": name, "path": str(destination), "sha256": source_hash})

    print(json.dumps({"status": "installed", "stages": installed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
