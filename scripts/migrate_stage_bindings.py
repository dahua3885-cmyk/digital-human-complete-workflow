#!/usr/bin/env python3
"""Migrate exact legacy example bindings to bundled public stage Skills."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


LEGACY_AVATAR = {"your-digital-human-video-skill", "replace-with-digital-human-video-skill"}
PUBLIC_AVATAR = "digital-human-avatar-musetalk"


def atomic_json(path: Path, payload: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    profile_path = args.profile.expanduser().resolve()
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"无法更新数字人阶段绑定：{exc}", file=sys.stderr)
        return 2
    stages = profile.get("stage_skills")
    avatar = stages.get("avatar") if isinstance(stages, dict) else None
    if not isinstance(avatar, dict):
        print("无法更新数字人阶段绑定：流程资料缺少数字人画面阶段。", file=sys.stderr)
        return 2
    current = avatar.get("skill")
    if current in LEGACY_AVATAR:
        avatar["skill"] = PUBLIC_AVATAR
        avatar["bundled_path"] = "bundled-stages/digital-human-avatar-musetalk"
        atomic_json(profile_path, profile)
        print("数字人画面阶段已更新为内置 MuseTalk 1.5 Skill。")
        return 0
    if current == PUBLIC_AVATAR:
        print("数字人画面阶段已经使用内置 MuseTalk 1.5 Skill。")
        return 0
    print("检测到用户自定义的数字人画面阶段，未做覆盖。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
