#!/usr/bin/env python3
"""只迁移旧版精确示例绑定；不覆盖用户自定义的真实阶段。"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

PUBLIC = {
    "rewrite": "digital-human-rewrite-generic",
    "voice": "digital-human-voice-chatterbox",
    "avatar": "digital-human-avatar-musetalk",
    "packaging": "digital-human-packaging-fixed",
}
LEGACY = {
    "rewrite": {"your-video-rewrite-skill", "replace-with-generic-rewrite-skill"},
    "voice": {"your-authorized-voice-skill", "replace-with-authorized-voice-skill"},
    "avatar": {"your-digital-human-video-skill", "replace-with-digital-human-video-skill"},
    "packaging": {"your-video-packaging-skill", "replace-with-video-packaging-skill"},
}

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"): sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("profile", type=Path); args = parser.parse_args()
    path = args.profile.expanduser().resolve()
    try: profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"无法更新阶段绑定：{exc}", file=sys.stderr); return 2
    stages = profile.get("stage_skills")
    if not isinstance(stages, dict): print("无法更新阶段绑定：流程资料缺少 stage_skills。", file=sys.stderr); return 2
    changed: list[str] = []
    for stage, public_name in PUBLIC.items():
        entry = stages.get(stage)
        if not isinstance(entry, dict): continue
        if entry.get("skill") in LEGACY[stage]:
            entry["skill"] = public_name; entry["bundled_path"] = f"bundled-stages/{public_name}"; changed.append(stage)
    if changed:
        temporary = path.with_suffix(path.suffix + ".tmp"); temporary.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); os.replace(temporary, path)
        print("已更新旧版示例阶段：" + "、".join(changed) + "。用户自定义真实阶段未覆盖。")
    else:
        print("没有需要迁移的旧版示例绑定，用户自定义真实阶段未覆盖。")
    return 0

if __name__ == "__main__": raise SystemExit(main())
