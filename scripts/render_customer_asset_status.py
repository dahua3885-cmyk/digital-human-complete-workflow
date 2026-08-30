#!/usr/bin/env python3
"""Render internal asset-center statuses as customer-facing Chinese text."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


MODULE_LABELS = {
    "creator": "创作者资料",
    "voice": "数字人音频",
    "avatar": "数字人形象",
    "packaging": "剪辑包装",
}

COMMON_LABELS = {
    "needs_recalibration": "需要重新校准",
    "needs_review": "需要复核",
    "blocked": "暂时无法使用",
}


def customer_label(module: str, status: str) -> str:
    if status in COMMON_LABELS:
        return COMMON_LABELS[status]
    if module == "creator":
        return "已建立" if status == "ready" else "尚未建立"
    if module in {"voice", "avatar"}:
        return "已准备完成" if status == "ready" else "首次使用时准备"
    if module == "packaging":
        return "可直接使用" if status == "ready" else "使用时自动准备"
    return "需要确认"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_center", type=Path)
    args = parser.parse_args()

    try:
        data = json.loads(args.asset_center.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"无法读取准备情况：{exc}", file=sys.stderr)
        return 2

    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        print("无法读取准备情况：资料结构不完整", file=sys.stderr)
        return 2

    print("当前准备情况：")
    for module in ("creator", "voice", "avatar", "packaging"):
        entry = profiles.get(module, {})
        status = entry.get("status", "") if isinstance(entry, dict) else ""
        print(f"- {MODULE_LABELS[module]}：{customer_label(module, status)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
