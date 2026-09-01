#!/usr/bin/env python3
"""Create a local-first onboarding workspace without collecting personal data."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


VALID_MODULES = ("rewrite", "voice", "avatar", "packaging")
MODULE_STEPS = {
    "rewrite": ["creator_profile", "source_preferences", "professional_boundaries"],
    "voice": [
        "voice_authorization",
        "reference_recording",
        "source_qa",
        "model_identity_test",
        "three_style_blind_review",
        "validation_sample",
        "voice_profile_frozen",
    ],
    "avatar": [
        "likeness_authorization",
        "recording_brief_acknowledged",
        "reference_video",
        "source_qa",
        "representative_sample",
        "avatar_profile_frozen",
    ],
    "packaging": ["brand_assets", "source_rules", "cover_assets"],
}


def parse_modules(value: str) -> list[str]:
    if value == "all":
        return list(VALID_MODULES)
    modules = [item.strip() for item in value.split(",") if item.strip()]
    invalid = sorted(set(modules) - set(VALID_MODULES))
    if invalid:
        raise argparse.ArgumentTypeError(
            f"unknown module(s): {', '.join(invalid)}; choose from {', '.join(VALID_MODULES)}"
        )
    if not modules:
        raise argparse.ArgumentTypeError("select at least one module")
    return list(dict.fromkeys(modules))


def write_text_new(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "workspace",
        type=Path,
        help="Local user workspace; unrelated existing files are preserved",
    )
    parser.add_argument(
        "--modules",
        type=parse_modules,
        default=list(VALID_MODULES),
        help="all or comma-separated rewrite,voice,avatar,packaging",
    )
    parser.add_argument(
        "--creator-profile",
        choices=("quick", "pro"),
        default="quick",
        help="Creator-profile template copied into the workspace",
    )
    args = parser.parse_args()

    workspace = args.workspace.expanduser().resolve()
    skill_root = Path(__file__).resolve().parent.parent
    assets = skill_root / "assets"
    user_manual = skill_root / "数字人完整流程.md"
    start_here = skill_root / "开始使用前请先填写.md"
    status_path = workspace / "profiles" / "onboarding-status.json"

    if status_path.exists():
        print(f"ERROR: onboarding already initialized: {status_path}", file=sys.stderr)
        return 2
    template_name = (
        "creator-profile-quick.template.md"
        if args.creator_profile == "quick"
        else "creator-profile-pro.template.md"
    )
    required_assets = (
        user_manual,
        start_here,
        assets / template_name,
        assets / "creator-profile-quick.template.md",
        assets / "creator-profile-pro.template.md",
        assets / "lawful-use-and-consent-declaration.template.md",
        assets / "preflight-intake-checklist.md",
        assets / "voice-recording-guide.md",
        assets / "avatar-recording-checklist.md",
        assets / "workflow-profile.example.json",
        assets / "runtime-config.example.json",
        assets / "consent-record.example.json",
        assets / "voice-profile.example.json",
        assets / "asset-center.example.json",
        assets / "avatar-profile.example.json",
        assets / "packaging-profile.example.json",
        assets / "rewrite-feedback.template.md",
        assets / "voice-feedback.template.md",
        assets / "avatar-feedback.template.md",
        assets / "packaging-feedback.template.md",
    )
    missing = [str(path) for path in required_assets if not path.is_file()]
    if missing:
        print(f"ERROR: missing bundled asset(s): {', '.join(missing)}", file=sys.stderr)
        return 2

    planned_outputs = [
        workspace / "profiles" / "creator-profile.md",
        workspace / "数字人完整流程.md",
        workspace / "开始使用前请先填写.md",
        workspace / "forms" / "创作者资料-简洁版.md",
        workspace / "forms" / "创作者资料-专业版.md",
        workspace / "forms" / "合法使用与授权声明.md",
        workspace / "profiles" / "workflow-profile.json",
        workspace / "profiles" / "runtime-config.json",
        workspace / "profiles" / "asset-center.json",
        workspace / ".private" / "consent" / "lawful-use-and-consent-declaration.md",
        workspace / "guides" / "voice-recording-guide.md",
        workspace / "guides" / "avatar-recording-checklist.md",
        workspace / "feedback" / "rewrite-feedback.md",
        workspace / "feedback" / "voice-feedback.md",
        workspace / "feedback" / "avatar-feedback.md",
        workspace / "feedback" / "packaging-feedback.md",
        workspace / ".private" / ".gitignore",
        status_path,
    ]
    if "voice" in args.modules or "avatar" in args.modules:
        planned_outputs.append(
            workspace / ".private" / "consent" / "consent-record.json"
        )
    if "voice" in args.modules:
        planned_outputs.append(workspace / ".private" / "voice" / "voice-profile.json")
    if "avatar" in args.modules:
        planned_outputs.append(
            workspace / ".private" / "avatar" / "avatar-profile.json"
        )
    if "packaging" in args.modules:
        planned_outputs.append(workspace / "profiles" / "packaging-profile.json")
    conflicts = [str(path) for path in planned_outputs if path.exists()]
    if conflicts:
        print(
            "ERROR: onboarding would overwrite existing managed file(s): "
            + ", ".join(conflicts),
            file=sys.stderr,
        )
        return 2

    directories = (
        workspace / "profiles",
        workspace / "projects",
        workspace / "brand-assets",
        workspace / "feedback",
        workspace / "forms",
        workspace / "guides",
        workspace / ".private" / "consent",
        workspace / ".private" / "identity",
        workspace / ".private" / "voice",
        workspace / ".private" / "avatar",
    )
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(assets / template_name, workspace / "profiles" / "creator-profile.md")
    shutil.copyfile(user_manual, workspace / "数字人完整流程.md")
    shutil.copyfile(start_here, workspace / "开始使用前请先填写.md")
    shutil.copyfile(
        assets / "creator-profile-quick.template.md",
        workspace / "forms" / "创作者资料-简洁版.md",
    )
    shutil.copyfile(
        assets / "creator-profile-pro.template.md",
        workspace / "forms" / "创作者资料-专业版.md",
    )
    shutil.copyfile(
        assets / "lawful-use-and-consent-declaration.template.md",
        workspace / "forms" / "合法使用与授权声明.md",
    )
    shutil.copyfile(
        assets / "workflow-profile.example.json",
        workspace / "profiles" / "workflow-profile.json",
    )
    shutil.copyfile(
        assets / "runtime-config.example.json",
        workspace / "profiles" / "runtime-config.json",
    )
    asset_center = json.loads(
        (assets / "asset-center.example.json").read_text(encoding="utf-8")
    )
    selected_modules = list(args.modules)
    for module, profile_key in (
        ("rewrite", "creator"),
        ("voice", "voice"),
        ("avatar", "avatar"),
        ("packaging", "packaging"),
    ):
        if module not in selected_modules:
            asset_center["profiles"][profile_key]["status"] = "not_selected"
            asset_center["profiles"][profile_key]["needs_attention_reason"] = None
    asset_center["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_text_new(
        workspace / "profiles" / "asset-center.json",
        json.dumps(asset_center, ensure_ascii=False, indent=2) + "\n",
    )
    shutil.copyfile(
        assets / "lawful-use-and-consent-declaration.template.md",
        workspace / ".private" / "consent" / "lawful-use-and-consent-declaration.md",
    )
    shutil.copyfile(
        assets / "voice-recording-guide.md",
        workspace / "guides" / "voice-recording-guide.md",
    )
    shutil.copyfile(
        assets / "avatar-recording-checklist.md",
        workspace / "guides" / "avatar-recording-checklist.md",
    )
    for template, destination in (
        ("rewrite-feedback.template.md", "rewrite-feedback.md"),
        ("voice-feedback.template.md", "voice-feedback.md"),
        ("avatar-feedback.template.md", "avatar-feedback.md"),
        ("packaging-feedback.template.md", "packaging-feedback.md"),
    ):
        shutil.copyfile(assets / template, workspace / "feedback" / destination)
    if "voice" in args.modules or "avatar" in args.modules:
        shutil.copyfile(
            assets / "consent-record.example.json",
            workspace / ".private" / "consent" / "consent-record.json",
        )
    if "voice" in args.modules:
        shutil.copyfile(
            assets / "voice-profile.example.json",
            workspace / ".private" / "voice" / "voice-profile.json",
        )
    if "avatar" in args.modules:
        shutil.copyfile(
            assets / "avatar-profile.example.json",
            workspace / ".private" / "avatar" / "avatar-profile.json",
        )
    if "packaging" in args.modules:
        shutil.copyfile(
            assets / "packaging-profile.example.json",
            workspace / "profiles" / "packaging-profile.json",
        )
    write_text_new(workspace / ".private" / ".gitignore", "*\n!.gitignore\n")

    module_status = {}
    for module in VALID_MODULES:
        selected = module in selected_modules
        default_status = "pending"
        module_status[module] = {
            "selected": selected,
            "status": default_status if selected else "not_selected",
            "steps": {
                step: default_status if selected else "not_selected"
                for step in MODULE_STEPS[module]
            },
        }

    status = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "deployment_mode": "local_open_source",
        "privacy": {
            "uploads_to_maintainer": False,
            "private_assets_committed": False,
        },
        "lawful_use_declaration": "pending",
        "identity_authorization": "pending",
        "creator_profile_type": args.creator_profile,
        "asset_center": "./asset-center.json",
        "modules": module_status,
        "ready_entry_modes": [],
        "next_action": "阅读《数字人完整流程》，在《开始使用前请先填写》中选择简洁版或专业版，填写后复制所选版本全部文字并发送回聊天。",
    }
    write_text_new(
        status_path, json.dumps(status, ensure_ascii=False, indent=2) + "\n"
    )

    print(f"PASS: local onboarding workspace created: {workspace}")
    print(f"Selected modules: {', '.join(selected_modules)}")
    print(f"Creator profile: {workspace / 'profiles' / 'creator-profile.md'}")
    print(f"Complete workflow guide: {workspace / '数字人完整流程.md'}")
    print(f"Start here: {workspace / '开始使用前请先填写.md'}")
    print(f"Status: {status_path}")
    print("No voice, likeness, identity document, or secret was uploaded or collected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
