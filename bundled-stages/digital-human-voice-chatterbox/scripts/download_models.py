#!/usr/bin/env python3
"""Download only the pinned public Chatterbox multilingual runtime files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from huggingface_hub import snapshot_download


REVISION = "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"
FILES = ["ve.pt", "t3_mtl23ls_v3.safetensors", "s3gen.pt", "grapheme_mtl_merged_expanded_v1.json", "conds.pt", "Cangjie5_TC.json"]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    args = parser.parse_args()
    target = args.model_dir.expanduser().resolve()
    try:
        snapshot_download(
            repo_id="ResembleAI/chatterbox",
            revision=REVISION,
            allow_patterns=FILES,
            local_dir=str(target),
        )
        missing = [name for name in FILES[:4] if not (target / name).is_file()]
        if missing:
            raise RuntimeError("下载完成后仍缺少：" + "、".join(missing))
        (target / "model-source.json").write_text(
            json.dumps({"repo_id": "ResembleAI/chatterbox", "revision": REVISION, "license": "MIT"}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("声音公开模型已下载并登记。")
        return 0
    except Exception as exc:
        print(f"声音模型下载未完成：{exc}。网络恢复后可安全重试，已下载文件会继续复用。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
