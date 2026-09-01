#!/usr/bin/env python3
"""Download pinned public MuseTalk inference models and record local hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


STAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = STAGE_ROOT / "assets" / "public-models.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_direct(url: str, target: Path, expected_sha256: str) -> None:
    if target.is_file() and sha256(target) == expected_sha256:
        return
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("当前 Python 环境缺少 requests，无法下载公开人脸检测模型。") from exc
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    headers: dict[str, str] = {}
    mode = "wb"
    if partial.is_file() and partial.stat().st_size:
        headers["Range"] = f"bytes={partial.stat().st_size}-"
        mode = "ab"
    with requests.get(url, headers=headers, stream=True, timeout=60) as response:
        if response.status_code == 200 and mode == "ab":
            mode = "wb"
        response.raise_for_status()
        with partial.open(mode) as stream:
            for block in response.iter_content(chunk_size=1024 * 1024):
                if block:
                    stream.write(block)
    actual = sha256(partial)
    if actual != expected_sha256:
        raise RuntimeError(f"公开人脸检测模型校验失败：期望 {expected_sha256}，实际 {actual}")
    partial.replace(target)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="Prepared MuseTalk runtime directory")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    repo = args.repo.expanduser().resolve()
    plan = {
        "repo": str(repo),
        "models": manifest["models"],
        "privacy": "只下载公开模型，不读取或上传声音、肖像和用户视频",
    }
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("当前 Python 环境缺少 huggingface-hub，无法下载公开模型。", file=sys.stderr)
        return 2

    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    records: list[dict[str, object]] = []
    try:
        for item in manifest["models"]:
            if "url" in item:
                target = repo / item["target_path"]
                download_direct(item["url"], target, item["sha256"])
                records.append(
                    {
                        "source": item["url"],
                        "revision": None,
                        "path": target.relative_to(repo).as_posix(),
                        "bytes": target.stat().st_size,
                        "sha256": sha256(target),
                    }
                )
                continue
            repo_id = item["repo_id"]
            revision = item["revision"]
            patterns = list(item["allow_patterns"])
            target = repo / item["target_dir"]
            target.mkdir(parents=True, exist_ok=True)
            snapshot_download(repo_id=repo_id, revision=revision, allow_patterns=patterns, local_dir=target)
            downloaded: list[Path] = []
            for relative in patterns:
                path = target / relative
                if not path.is_file():
                    raise FileNotFoundError(f"公开模型下载后仍缺少：{repo_id}/{relative}")
                downloaded.append(path)
            for path in downloaded:
                records.append({"source": repo_id, "revision": revision, "path": path.relative_to(repo).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    except Exception as exc:
        print(f"公开模型下载或校验没有完成：{exc}。已下载的分片会保留，下次可以继续。", file=sys.stderr)
        return 2

    output = repo / "models-manifest.local.json"
    output.write_text(
        json.dumps({"schema_version": 1, "files": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"公开模型下载并校验完成：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
