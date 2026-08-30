#!/usr/bin/env python3
"""Validate and save one completed creator profile, then update local readiness."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


CUSTOMER_MESSAGE = "个人资料已建立，数字人全流程和分别制作均可使用。"
VERSION_RE = re.compile(r"^资料版本[ \t]*[：:][ \t]*(.+?)[ \t]*$", re.MULTILINE)
FIELD_RE = re.compile(r"^([^\n：:]+?)[ \t]*[：:][ \t]*(.*?)[ \t]*$", re.MULTILINE)

REQUIRED_FIELDS = {
    "基础信息简洁版": (
        "账号称呼",
        "职业 / 身份",
        "行业或内容领域",
        "核心受众",
        "受众最常见的3个问题",
        "长期想讲的3–5个内容方向",
        "希望带来的价值或账号目标",
        "表达风格",
        "不希望出现的表达或内容",
        "资质边界、地区限制或免责声明",
    ),
    "基础信息专业版": (
        "账号称呼",
        "职业 / 身份及从业方向",
        "行业或内容领域",
        "核心受众及其所处阶段",
        "受众常见的问题、误区或顾虑",
        "长期内容方向或固定栏目",
        "希望带来的价值及账号目标",
        "不能出现的表达、承诺或敏感内容",
        "资质边界、地区限制或免责声明",
        "语气、句长、信息密度和节奏",
        "喜欢的开头、内容结构和结尾",
        "不喜欢的AI腔或营销话术",
        "可以接受和不能接受的行动引导",
    ),
}


def atomic_write_text(path: Path, content: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("profile_source", type=Path)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace a previously established creator profile",
    )
    args = parser.parse_args()

    workspace = args.workspace.expanduser().resolve()
    source = args.profile_source.expanduser().resolve()
    profile_path = workspace / "profiles" / "creator-profile.md"
    asset_center_path = workspace / "profiles" / "asset-center.json"
    onboarding_path = workspace / "profiles" / "onboarding-status.json"

    if not source.is_file():
        print("无法建立个人资料：没有找到填写完成的资料。", file=sys.stderr)
        return 2
    if not asset_center_path.is_file() or not onboarding_path.is_file():
        print("无法建立个人资料：当前工作区尚未完成首次初始化。", file=sys.stderr)
        return 2

    try:
        content = source.read_text(encoding="utf-8-sig").strip() + "\n"
        asset_center = json.loads(asset_center_path.read_text(encoding="utf-8"))
        onboarding = json.loads(onboarding_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"无法建立个人资料：资料文件读取失败（{exc}）。", file=sys.stderr)
        return 2

    version_match = VERSION_RE.search(content)
    version = version_match.group(1).strip() if version_match else ""
    required = REQUIRED_FIELDS.get(version)
    if required is None:
        print(
            "无法识别资料版本：请保留“资料版本：基础信息简洁版”或“资料版本：基础信息专业版”。",
            file=sys.stderr,
        )
        return 2

    fields = {key.strip(): value.strip() for key, value in FIELD_RE.findall(content)}
    missing = [label for label in required if not fields.get(label)]
    if missing:
        print(
            "以下必填项还没有内容：" + "、".join(missing) + "。请只补充这些项目，不需要重填整份资料。",
            file=sys.stderr,
        )
        return 2

    creator = asset_center.get("profiles", {}).get("creator", {})
    if not isinstance(creator, dict):
        print("无法建立个人资料：创作者资料状态结构不完整。", file=sys.stderr)
        return 2
    existing_ready = creator.get("status") == "ready"
    existing_content = profile_path.read_text(encoding="utf-8") if profile_path.is_file() else ""
    if existing_ready and existing_content.strip() == content.strip():
        print(CUSTOMER_MESSAGE)
        return 0
    if existing_ready and not args.replace:
        print("个人资料已经建立。如需覆盖原资料，请明确要求更新个人资料。", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc).isoformat()
    atomic_write_text(profile_path, content)
    creator["status"] = "ready"
    creator["sha256"] = sha256_text(content)
    creator["needs_attention_reason"] = None
    asset_center["updated_at"] = now
    atomic_write_json(asset_center_path, asset_center)

    modules = onboarding.setdefault("modules", {})
    rewrite = modules.setdefault("rewrite", {})
    rewrite["selected"] = True
    rewrite["status"] = "ready"
    steps = rewrite.setdefault("steps", {})
    for key in ("creator_profile", "source_preferences", "professional_boundaries"):
        steps[key] = "ready"
    ready_entries = onboarding.setdefault("ready_entry_modes", [])
    for entry in ("rewrite", "packaging_only"):
        if entry not in ready_entries:
            ready_entries.append(entry)
    onboarding["creator_profile_type"] = (
        "quick" if version == "基础信息简洁版" else "pro"
    )
    onboarding["updated_at"] = now
    onboarding["next_action"] = "可以发送视频链接、文案或待包装视频，并说明本次要制作的内容。"
    atomic_write_json(onboarding_path, onboarding)

    print(CUSTOMER_MESSAGE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
