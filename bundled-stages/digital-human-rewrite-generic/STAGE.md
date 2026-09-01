---
name: digital-human-rewrite-generic
description: Create an original, profile-aware Chinese talking-head script from a video link, local video, transcript, or user material, then produce a validated script handoff for the digital-human workflow. Use only for the rewrite stage; stop for explicit script approval before voice generation.
metadata:
  version: "1.0.0"
---

# 通用二创文案

这是随数字人完整流程发行的真实二创阶段，不是示例名称。它使用 Codex 的网页读取、视频/音频转写与写作能力，不依赖某位创作者的私人路径或资料。

## 开工

1. 读取总流程提供的 `creator-profile.md`、任务订单、来源与合法使用声明。
2. 链接可访问时读取原始页面并取得可核验内容；本地视频或音频先转写。无法访问链接时只针对该链接说明网络或访问问题，不虚构原内容。
3. 涉及政策、价格、产品版本、行业新闻或专业高风险事实时，检索当前公开权威来源。英文品牌或产品名按总流程的中文语境发音规则核验。
4. 建立 `source-record.md`、`topic-card.md`、`source-contribution.md`、`rewrite-decision.md`、`final-script.md` 与 `qa-report.md`。禁止只换同义词；最终文案必须重新组织结构、论证与表达。

## 交付与闸门

- 先展示完整干净口播稿，等待用户明确确认或修改。
- 未确认时不得建立批准交接物，也不得进入数字人音频。
- 确认后运行 `scripts/create_script_handoff.py`，把来源、最终稿、QA、用户确认和任务编号绑定到同一份 SHA-256 交接物。
- 最终显示一级标题 `# 是否继续生成数字人音频？`，下方只给“继续生成数字人音频 / 复制文案并结束任务”。继续时由任务订单自动传递交接物，不让用户复制粘贴。

## 质量底线

- 不把创作者未提供的资历、案例、收入、客户结果或个人经历写成事实。
- 简洁版资料已填写完整时不得追加第二套问卷；只有当前题目缺少不可安全推断的单项事实才询问该项。
- 交付稿应口语自然、逻辑清楚、符合人物行业边界，并记录事实来源、原创性与可口播性检查。
