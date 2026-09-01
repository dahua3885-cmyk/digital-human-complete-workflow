---
name: digital-human-packaging-fixed
description: Package an authorized existing digital-human or single-speaker video into the workflow's fixed 1080x1920 black-and-cyan information layout, with a bottom-right speaker window, timed cards, captions, three cover ratios, technical QA, and delivery manifest. Use only for the packaging stage.
metadata:
  version: "1.0.0"
---

# 剪辑包装

本阶段随公开包提供固定执行器，不再要求使用者另找示例剪辑 Skill。用户侧名称始终是“剪辑包装”，不显示历史版本编号或让用户选择版式。

## 固定结果

- 1080×1920、30fps、H.264、AAC。
- 深黑/深海军蓝背景与青蓝强调；主要信息在上部，人物视频固定右下角。
- 字幕与信息卡由真实文案和转写驱动，不编造产品界面、案例、数据或资质。
- 必交无封面母版、带约 0.1 秒封面的发布版、9:16 / 3:4 / 1:1 三张独立封面、工程数据、QA 报告和 `delivery-manifest.json`。

## 运行

1. 运行 `python scripts/check_runtime.py --json`；未就绪时运行 `python scripts/setup_runtime.py`。Windows 子进程隐藏运行。
2. 对来源视频做授权、时长、解码、音轨和人物裁切检查。包装阶段不重新克隆声音或改变用户已确认音频。
3. 制作前建立 `content-hierarchy.md`、`timeline.json`（信息卡）和 `captions.json`（字幕）。卡片内容解释口播，不机械复述字幕；真实素材缺失时不用示意图冒充证据。
4. 先用代表性 5–12 秒片段内部检查人物裁切、字幕、安全区与信息卡，再执行全片。
5. 运行 `render_package.py`。脚本保留源音轨、生成三张封面、给发布版预留封面时间，并写入 QA 与交付清单。

示例：

```powershell
python scripts/render_package.py --source input.mp4 --title "本期主题" --cards timeline.json --captions captions.json --output-dir outputs
```

`timeline.json` 是 `[{"start":0.5,"end":6.0,"kicker":"重点","title":"核心结论","body":"解释文字"}]`；`captions.json` 是 `[{"start":0.2,"end":2.1,"text":"字幕文字"}]`。所有文字必须来自已确认文案或真实证据。

最终发布版保留“AI 生成内容”标识，不得删除或隐匿。
