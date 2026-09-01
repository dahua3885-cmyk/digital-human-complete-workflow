#!/usr/bin/env python3
"""在生产开始前真实调用各阶段运行检查；不接受手工布尔值冒充就绪。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


STAGES = ("rewrite", "voice", "avatar", "packaging")
SKILL_NAME_RE = re.compile(r"^name:\s*([a-z0-9]+(?:-[a-z0-9]+)*)\s*$", re.MULTILINE)


def hidden_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def resolve_path(base: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def discover_skill_root(name: str, workflow_root: Path) -> Path | None:
    candidates = [workflow_root / "bundled-stages" / name, workflow_root.parent / name]
    codex_home = os.getenv("CODEX_HOME")
    if codex_home:
        candidates.append(Path(codex_home).expanduser() / "skills" / name)
    candidates.append(Path.home() / ".codex" / "skills" / name)
    for candidate in candidates:
        resolved = candidate.resolve()
        if (resolved / "SKILL.md").is_file():
            return resolved
    return None


def run_probe(stage: str, skill_root: Path, entry: dict[str, object], config_dir: Path) -> tuple[bool, list[str]]:
    probe_value = entry.get("runtime_probe", "scripts/check_runtime.py")
    if not isinstance(probe_value, str) or not probe_value.strip():
        return False, [f"{stage} 阶段没有声明运行检查脚本"]
    probe = resolve_path(skill_root, probe_value)
    try:
        probe.relative_to(skill_root.resolve())
    except ValueError:
        return False, [f"{stage} 阶段运行检查脚本超出 Skill 目录"]
    if not probe.is_file():
        return False, [f"{stage} 阶段缺少运行检查脚本：{probe_value}"]
    command = [sys.executable, str(probe), "--json"]
    runtime_config = entry.get("runtime_config")
    if isinstance(runtime_config, str) and runtime_config.strip():
        command.extend(["--config", str(resolve_path(config_dir, runtime_config))])
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=hidden_flags(),
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        detail = completed.stderr.strip() or completed.stdout.strip() or "没有返回可解析结果"
        return False, [f"{stage} 阶段运行检查异常：{detail}"]
    if completed.returncode == 0 and payload.get("ready") is True:
        return True, []
    problems = payload.get("problems_zh")
    if not isinstance(problems, list) or not all(isinstance(item, str) for item in problems):
        problems = [completed.stderr.strip() or f"{stage} 阶段尚未准备完成"]
    return False, [f"{stage}：{item}" for item in problems if item]


def supplemental_checks(entry: dict[str, object], config_dir: Path) -> list[str]:
    errors: list[str] = []
    checks = entry.get("checks", [])
    if not isinstance(checks, list):
        return ["补充检查配置必须是列表"]
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            errors.append(f"补充检查第 {index + 1} 项格式不正确")
            continue
        kind = check.get("type")
        value = check.get("value")
        if not isinstance(value, str) or not value.strip() or value.startswith("replace-"):
            errors.append(f"补充检查第 {index + 1} 项没有配置有效值")
        elif kind == "command" and not (Path(value).is_file() or shutil.which(value)):
            errors.append(f"没有找到命令：{value}")
        elif kind == "path" and not resolve_path(config_dir, value).exists():
            errors.append(f"没有找到路径：{value}")
        elif kind == "env" and not os.getenv(value):
            errors.append(f"没有设置环境变量：{value}")
        elif kind == "python_module" and importlib.util.find_spec(value) is None:
            errors.append(f"没有找到 Python 模块：{value}")
        elif kind not in {"command", "path", "env", "python_module"}:
            errors.append(f"不支持的补充检查类型：{kind}")
    return errors


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--stages", help="只检查逗号分隔的阶段；默认检查 enabled_stages")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    config_path = args.config.expanduser().resolve()
    workflow_root = Path(__file__).resolve().parents[1]
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"运行配置无法读取：{exc}", file=sys.stderr)
        return 2

    enabled = config.get("enabled_stages")
    stages = config.get("stages")
    if not isinstance(enabled, list) or not isinstance(stages, dict):
        print("运行配置缺少 enabled_stages 或 stages。", file=sys.stderr)
        return 2
    requested = [item.strip() for item in args.stages.split(",")] if args.stages else enabled
    if not requested or any(item not in STAGES or item not in enabled for item in requested):
        print("要检查的阶段无效或尚未启用。", file=sys.stderr)
        return 2

    ready: list[str] = []
    problems: list[str] = []
    for stage in requested:
        entry = stages.get(stage)
        if not isinstance(entry, dict):
            problems.append(f"{stage}：缺少阶段配置")
            continue
        name = entry.get("skill_name")
        if not isinstance(name, str) or not name or name.startswith(("replace-", "your-")):
            problems.append(f"{stage}：尚未绑定真实阶段 Skill")
            continue
        root_value = entry.get("skill_root")
        skill_root = (
            resolve_path(config_path.parent, root_value)
            if isinstance(root_value, str) and root_value.strip()
            else discover_skill_root(name, workflow_root)
        )
        if skill_root is None:
            problems.append(f"{stage}：没有找到阶段 Skill {name}")
            continue
        try:
            match = SKILL_NAME_RE.search((skill_root / "SKILL.md").read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            match = None
        if match is None or match.group(1) != name:
            problems.append(f"{stage}：阶段 Skill 名称或文件不匹配")
            continue
        if entry.get("adapter_contract_version") != 1:
            problems.append(f"{stage}：阶段适配器版本不兼容")
            continue
        ok, probe_problems = run_probe(stage, skill_root, entry, config_path.parent)
        extra = supplemental_checks(entry, config_path.parent)
        if ok and not extra:
            ready.append(stage)
        else:
            problems.extend(probe_problems + [f"{stage}：{item}" for item in extra])

    payload = {"ready": not problems, "checked_stages": requested, "ready_stages": ready, "problems_zh": problems}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif problems:
        print("当前还不能开始：" + "；".join(problems) + "。", file=sys.stderr)
    else:
        print("所需阶段运行环境已准备完成：" + "、".join(ready) + "。")
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
