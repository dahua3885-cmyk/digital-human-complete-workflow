#!/usr/bin/env python3
"""Copy first-use documents into the active workspace and print the welcome text."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from urllib.parse import quote


DOCUMENTS = ("数字人完整流程.md", "开始使用前请先填写.md")
OUTPUT_FOLDER = "数字人完整流程资料"
REPOSITORY_URL = "https://github.com/dahua3885-cmyk/digital-human-complete-workflow"


def files_match(folder: Path, sources: dict[str, bytes]) -> bool:
    return all(
        (folder / name).is_file() and (folder / name).read_bytes() == content
        for name, content in sources.items()
    )


def choose_output_folder(base: Path, version: str, sources: dict[str, bytes]) -> Path:
    first = base / version
    if not first.exists() or files_match(first, sources):
        return first

    digest = hashlib.sha256(b"\0".join(sources[name] for name in DOCUMENTS)).hexdigest()[:8]
    numbered = base / f"{version}-{digest}"
    counter = 2
    while numbered.exists() and not files_match(numbered, sources):
        numbered = base / f"{version}-{digest}-{counter}"
        counter += 1
    return numbered


def markdown_target(path: Path) -> str:
    return f"<{path.resolve().as_posix()}>"


def welcome_markdown(manual_target: str, profile_target: str) -> str:
    return (
        "数字人完整流程 Skill 已安装完成。\n\n"
        f"为了更好地使用，请先阅读“[数字人完整流程使用手册]({manual_target})”，"
        f"再填写“[开始使用前请先填写]({profile_target})”。\n\n"
        "资料表中有基础信息简洁版和专业版，请选择一个版本填写。"
        "填写完成后，复制所选版本的全部文字并发送给我，我会为你建立个人资料。"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path, help="Current Codex task workspace")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Print the customer welcome text or a structured handoff for Codex",
    )
    args = parser.parse_args()

    workspace = args.workspace.expanduser().resolve()
    if not workspace.is_dir():
        print(f"ERROR: workspace does not exist or is not a directory: {workspace}", file=sys.stderr)
        return 1

    skill_root = Path(__file__).resolve().parents[1]
    if workspace == skill_root or skill_root in workspace.parents:
        print("ERROR: choose the active task workspace, not the Skill installation directory", file=sys.stderr)
        return 1

    manifest_path = skill_root / "distribution-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        version = str(manifest["package_version"])
        sources = {name: (skill_root / name).read_bytes() for name in DOCUMENTS}
    except (OSError, UnicodeError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot prepare first-use documents: {exc}", file=sys.stderr)
        return 1

    output_root = workspace / OUTPUT_FOLDER
    output_dir = choose_output_folder(output_root, version, sources)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in sources.items():
        destination = output_dir / name
        if not destination.exists() or destination.read_bytes() != content:
            temporary = destination.with_name(destination.name + ".tmp")
            temporary.write_bytes(content)
            temporary.replace(destination)
            shutil.copystat(skill_root / name, destination)

    manual_path = (output_dir / DOCUMENTS[0]).resolve()
    profile_path = (output_dir / DOCUMENTS[1]).resolve()
    local_welcome = welcome_markdown(
        markdown_target(manual_path), markdown_target(profile_path)
    )
    online_welcome = welcome_markdown(
        f"{REPOSITORY_URL}/blob/main/{quote(DOCUMENTS[0])}",
        f"{REPOSITORY_URL}/blob/main/{quote(DOCUMENTS[1])}",
    )

    if args.format == "json":
        print(
            json.dumps(
                {
                    "status": "DOCS_READY",
                    "manual_path": str(manual_path),
                    "profile_path": str(profile_path),
                    "welcome_markdown": online_welcome,
                    "local_welcome_markdown": local_welcome,
                },
                ensure_ascii=True,
            )
        )
    else:
        print(online_welcome)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
