#!/usr/bin/env python3
"""Regression-test the customer journey from first activation through task routing."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
EXACT_PROFILE_SUCCESS = "个人资料已建立，数字人全流程和分别制作均可使用。"
INTERNAL_CUSTOMER_TOKENS = (
    "ready",
    "pending",
    "needs_recalibration",
    "needs_review",
    "not_selected",
    "blocked",
    "draft",
    "distribution_ok",
    "end_to_end",
    "runtime-config",
    ".codex/skills",
)


def run_script(name: str, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *arguments],
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )


def assert_no_internal_customer_tokens(text: str, label: str) -> None:
    lowered = text.lower()
    leaked = [token for token in INTERNAL_CUSTOMER_TOKENS if token in lowered]
    if leaked:
        raise AssertionError(f"{label} leaked internal customer tokens: {leaked}")


def quick_profile() -> str:
    return """资料版本：基础信息简洁版
【我的基本信息】
账号称呼：安心用工说
职业 / 身份：律师
行业或内容领域：劳动法与企业用工合规

【我的受众与内容】
核心受众：需要降低用工风险的中小企业负责人
受众最常见的3个问题：合同怎么签、员工怎么管、证据怎么留
长期想讲的3–5个内容方向：合同避坑、劳动用工、证据清单、案例复盘
希望带来的价值或账号目标：用清楚的普法内容帮助企业提前避险

【我的表达与边界】
表达风格：专业、清楚、不过度营销
可公开的真实经历、资源或案例：暂无
不希望出现的表达或内容：不夸大结果，不承诺胜诉
本人文案、逐字稿或视频链接：暂无
资质边界、地区限制或免责声明：内容仅作普法分享，不构成针对个案的法律意见
"""


def main() -> int:
    install_prompt = (SKILL_ROOT / "安装话术.md").read_text(encoding="utf-8")
    if "安装并立即启用" not in install_prompt:
        raise AssertionError("install prompt must request installation and activation in one message")
    if "https://github.com/dahua3885-cmyk/digital-human-complete-workflow" not in install_prompt:
        raise AssertionError("install prompt has no public repository URL")

    with tempfile.TemporaryDirectory(prefix="数字人客户全流程 空格 ") as temporary:
        workspace = Path(temporary)
        unrelated = workspace / "客户原有项目.txt"
        unrelated.write_text("不得删除或覆盖\n", encoding="utf-8")

        prepared = run_script(
            "prepare_first_use_docs.py", str(workspace), "--format", "json"
        )
        handoff = json.loads(prepared.stdout)
        if handoff.get("status") != "DOCS_READY":
            raise AssertionError("first-use documents were not prepared")
        welcome = handoff["welcome_markdown"]
        if len(re.split(r"\n\s*\n", welcome.strip())) != 3:
            raise AssertionError("welcome must contain exactly three paragraphs")
        if welcome.count("https://github.com/") != 2:
            raise AssertionError("welcome must contain two public document links")
        assert_no_internal_customer_tokens(welcome, "welcome")
        for key in ("manual_path", "profile_path"):
            document = Path(handoff[key])
            document.resolve().relative_to(workspace.resolve())
            if not document.is_file():
                raise AssertionError(f"missing prepared document: {document}")
            visible = document.as_posix().lower()
            if "draft" in visible or re.search(r"/\d+\.\d+\.\d+(?:[-/]|$)", visible):
                raise AssertionError("visible document path exposes an internal version")

        initialized = run_script("init_user_workspace.py", str(workspace))
        if initialized.returncode != 0:
            raise AssertionError("initialization failed after first-use documents were prepared")
        if unrelated.read_text(encoding="utf-8") != "不得删除或覆盖\n":
            raise AssertionError("initialization changed an unrelated customer file")
        workflow_profile = json.loads(
            (workspace / "profiles" / "workflow-profile.json").read_text(encoding="utf-8")
        )
        if workflow_profile["stage_skills"]["avatar"]["skill"] != "digital-human-avatar-musetalk":
            raise AssertionError("new customers still receive an example avatar binding")

        profile_source = workspace / "已填写资料.md"
        profile_source.write_text(quick_profile(), encoding="utf-8")
        saved = run_script("save_creator_profile.py", str(workspace), str(profile_source))
        if saved.stdout.strip() != EXACT_PROFILE_SUCCESS or saved.stderr:
            raise AssertionError(f"unexpected profile reply: {saved.stdout!r} {saved.stderr!r}")
        assert_no_internal_customer_tokens(saved.stdout, "profile success reply")

        saved_again = run_script("save_creator_profile.py", str(workspace), str(profile_source))
        if saved_again.stdout.strip() != EXACT_PROFILE_SUCCESS or saved_again.stderr:
            raise AssertionError("saving the same profile must be idempotent")

        status = run_script(
            "render_customer_asset_status.py",
            str(workspace / "profiles" / "asset-center.json"),
        )
        for expected in (
            "创作者资料：已建立",
            "数字人音频：首次使用时准备",
            "数字人形象：首次使用时准备",
            "剪辑包装：可直接使用",
        ):
            if expected not in status.stdout:
                raise AssertionError(f"missing Chinese status: {expected}")
        assert_no_internal_customer_tokens(status.stdout, "customer status")

        incomplete = workspace / "缺项资料.md"
        incomplete.write_text(
            quick_profile().replace("表达风格：专业、清楚、不过度营销", "表达风格："),
            encoding="utf-8",
        )
        rejected = run_script(
            "save_creator_profile.py", str(workspace), str(incomplete), check=False
        )
        if rejected.returncode == 0:
            raise AssertionError("an incomplete profile was accepted")
        if "表达风格" not in rejected.stderr or "不需要重填整份资料" not in rejected.stderr:
            raise AssertionError("missing-field reply is not specific or reassuring")
        assert_no_internal_customer_tokens(rejected.stderr, "missing-field reply")

        for project, entry, target, source_kind, source in (
            ("rewrite-test", "rewrite", "rewrite", "url", "https://example.com/video"),
            ("digital-human-test", "voice", "avatar", "text", "这是一段最终口播文案。"),
            ("packaging-test", "packaging", "packaging", "file", str(unrelated)),
            ("full-workflow-test", "rewrite", "packaging", "url", "https://example.com/full"),
        ):
            created = run_script(
                "create_task_order.py",
                str(workspace),
                "--project",
                project,
                "--entry",
                entry,
                "--target",
                target,
                "--source-kind",
                source_kind,
                "--source",
                source,
            )
            if "TASK_ORDER_CREATED:" not in created.stdout:
                raise AssertionError(f"task route was not created: {project}")

        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for heading in (
            "# 是否继续生成数字人音频？",
            "# 是否继续生成数字人画面？",
            "# 是否继续剪辑包装？",
        ):
            if heading not in skill_text:
                raise AssertionError(f"missing stage continuation heading: {heading}")

        second_init = run_script("init_user_workspace.py", str(workspace), check=False)
        if second_init.returncode == 0:
            raise AssertionError("a second initialization unexpectedly overwrote managed files")
        if unrelated.read_text(encoding="utf-8") != "不得删除或覆盖\n":
            raise AssertionError("repeat initialization changed an unrelated customer file")

    print("CUSTOMER_JOURNEY_TEST_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
