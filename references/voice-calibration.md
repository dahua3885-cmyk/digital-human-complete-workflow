# 声音个体化校准

## 为什么不能使用统一倍数

`0.70`、`0.82`、`1.0` 等数值只对特定模型、参数语义、参考声和人物有效。不同 TTS 对速度参数的方向、幅度和句长响应可能不同；同一个人在不同语言、情绪和文本类型中也会需要不同节奏。通版禁止把某个人已确认的倍率推广给其他人。

## 校准单位

通版保存两个层次：

1. **听感目标**：每秒语义单位、短句是否赶读、句速波动、停顿和收句方式。
2. **模型适配值**：被绑定声音 Skill 把听感目标转换为当前模型的 speed/rate/duration 参数。

不要假定数值越大一定越快，也不要跨模型复制倍率。

## 首次必须做三风格确认

本节是 [数字人音频首次建档](audio-onboarding.md) 的校准核心。为每个“人物 + 模型版本 + 参考声哈希 + 语言”单独建立 `voice-profile.json`；可从 [示例](../assets/voice-profile.example.json) 复制到项目私有目录：

1. 选取同一段 20–40 秒校准文本，覆盖短句、中句、长句、数字、英文/专业词、并列、转折和完整收句。
2. 先按 [中英文发音核验](pronunciation-research.md) 处理英文、品牌名、缩写和易错专业词。
3. 用完全相同的文案和参考声生成三种候选，并随机映射为 A/B/C：
   - `natural-balanced`（自然均衡）：从模型原生默认节奏开始，停顿自然、情绪克制，适合知识、法律、教育、企业等广泛场景。
   - `steady-integrated`（稳健融合）：短句略慢、句中停顿短、长句连续、句末收得清楚，强调稳定和语义连贯。这是当前专用流程风格的通用语义表达，不公开个人名称或固定倍率。
   - `short-video-compact`（短视频紧凑）：开头更利落、语义停顿更短，整体听感通常比自然均衡快约 5%–10%，但不赶读、不吞字。
4. 用户先在不知道风格名的情况下盲听 A/B/C，评价自然度、本人相似度、长期适用度和具体问题；选择后才揭示 `style_id`。记录随机映射、三份样本哈希、选择原话和时间。没有可靠行业统计可以证明第三种是“最多人使用”，所以只称为常见短视频实用预设。
5. 在用户选中的风格内，再以模型默认值为中心生成短/中/长句参数候选，由模型适配器决定参数方向。
6. 用另一段未参与选择的验证文本生成完整音频；通过主观试听与技术 QA 后冻结 Profile。以后默认沿用所选风格，不再每条重复询问。

### 专用倍率的适配边界

若绑定的声音 Skill 与专用 F5 适配器完全一致，可把长句 `0.82`、中句 `0.79`、短句 `0.70` 仅作为 `steady-integrated` 的首次起始点，再通过三风格试听校准。换人物、参考声、模型版本、语言或参数语义后这些数值不能直接复用，需要重新校准；公共界面不得把它们作为通版推荐。

## 自适应生成

- 先保留显示稿，再建立只处理发音、数字和停顿的 TTS 稿。
- 句末标点形成完整收句；句内分块必须保持语义连续。
- 根据每块的字符、数字、英文词、标点和语义作用选择已校准档位。
- 生成后测量每块实际语义单位/秒和全片句速分布；超过该人物 Profile 的上限时只重生受影响块。
- 数字、专业词和跨语言片段在真实前后文中试听并冻结完整语义块；英文、品牌和缩写必须有在线中文语境发音核验记录。
- 完整 WAV 仍需用户实际试听确认。校准 Profile 通过不等于每篇新音频自动通过。

## 需要重新校准的条件

模型/权重、参考声、语言、采样路线或核心声音参数改变时，为新组合建立新版 Profile 并重新校准；原 Profile 继续作为旧组合的历史记录。人物仅改变主题不要求重校准，但新语言、强情绪、唱歌或明显不同的表演风格需要新 Profile。

## 建议结构

```json
{
  "schema_version": 1,
  "subject_id": "local-private-id",
  "model": {"name": "...", "version": "...", "rate_direction": "adapter_defined"},
  "reference_audio": {"sha256": "...", "authorization_record": "..."},
  "language": "zh-CN",
  "selected_style": "natural-balanced | steady-integrated | short-video-compact",
  "style_candidates": {
    "natural-balanced": {"sample_sha256": "...", "approved": false},
    "steady-integrated": {"sample_sha256": "...", "approved": true},
    "short-video-compact": {"sample_sha256": "...", "approved": false}
  },
  "approved_rates": {
    "short": {"adapter_value": null, "sample_sha256": "..."},
    "medium": {"adapter_value": null, "sample_sha256": "..."},
    "long": {"adapter_value": null, "sample_sha256": "..."}
  },
  "pace_limits": {"target_units_per_second": null, "maximum_units_per_second": null},
  "pause_policy": {"phrase": null, "sentence": null, "section": null},
  "pronunciation_lexicon": [],
  "approved_at": "ISO-8601",
  "approval_text": "用户确认原话"
}
```

上述速度比例只是听感目标。不同引擎对 `speed`、`rate` 或 `duration` 的定义不同；模型适配器必须先验证参数方向。可参考 ElevenLabs 的通用建议：先从模型默认速度试起，在实际对话中试听，并用发音词典固化专有词；不能把其参数范围直接套到其他模型：<https://elevenlabs.io/docs/eleven-agents/customization/voice>。
