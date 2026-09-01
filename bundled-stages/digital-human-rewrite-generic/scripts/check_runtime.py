#!/usr/bin/env python3
"""Report readiness for the Codex-native rewrite stage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    missing = [name for name in ("SKILL.md", "scripts/create_script_handoff.py") if not (root / name).is_file()]
    result = {
        "ready": not missing,
        "provider": "codex-native-rewrite",
        "problems_zh": [f"二创阶段发行文件缺失：{name}" for name in missing],
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ready"]:
        print("二创阶段已准备完成。")
    else:
        print("二创阶段暂时不能开始：" + "；".join(result["problems_zh"]) + "。")
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
