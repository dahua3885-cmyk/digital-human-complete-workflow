---
name: digital-human-voice-chatterbox
description: Generate authorized Chinese digital-human voice audio with a locally installed, pinned Chatterbox multilingual runtime, one-time three-style calibration, reference-audio QA, and an approved audio handoff. Use for the voice stage only; never continue to avatar rendering before the user confirms the complete WAV.
metadata:
  version: "1.0.0"
---

# 通用数字人音频

本阶段使用公开的 Chatterbox 多语言声音模型，不包含任何维护者或用户的参考声。参考声、声音 Profile 与授权证据只存放在使用者本机私有目录。

## 首次运行准备

1. 运行 `python scripts/check_runtime.py --json`。未就绪时先说明需要一次性下载模型和依赖；取得用户同意后运行 `python scripts/setup_runtime.py --accept-large-download`。Windows 子进程必须隐藏运行。
2. 模型和代码许可、固定版本与下载范围见 [第三方说明](references/third-party-notices.md)。安装或下载错误只用中文说明“发生了什么、是否可重试、下一步”，不向客户输出 Python 堆栈。
3. 处理真人声音前必须核验声音授权、用途和最终发布者；第三方声音没有可验证授权时停止。

## 参考素材

- 建议用户录制 1–3 分钟连续、干净、单人、无音乐的母素材，以便挑选稳定片段；实际送入当前模型的参考片段建议 5–15 秒。
- 3 秒清晰单人语音属于“最低可尝试”，不得仅因时长为 3 秒直接拒绝；应先运行 `prepare_reference.py` 检查并明确提示相似度和稳定性可能较低。短于 3 秒、多人重叠、明显音乐/混响/削波才阻断。
- 视频素材先由 `prepare_reference.py` 提取单声道 WAV。母素材较长时由执行者挑选无遮挡、无口误、语气自然的连续片段，不盲用开头。

## 首次三风格与长期复用

同一人物、模型、参考声和语言组合只校准一次：

1. 用同一段校准文案生成 `natural`（自然均衡）、`steady`（稳健融合）、`compact`（短视频紧凑）。
2. 用户试听后选择一个，写入 `voice-profile.json`；后续视频自动沿用，不再重复三选一。
3. 每条视频仍须试听并确认该条完整音频。参考声、人物、模型或语言改变时才建立新 Profile 版本。

## 每条视频

1. 冻结显示稿，核对英文、品牌、缩写、数字和专业词的中国用户常见读法。
2. 先生成开头、最长句和英文/数字风险句；通过后运行 `render_chatterbox.py` 生成完整 WAV。
3. 做 ASR 对稿、响度、静音、重复、吞字、爆音和连续试听 QA。模型技术成功不能代替用户确认。
4. 用户明确确认完整 WAV 后运行 `create_audio_handoff.py`；交接物必须绑定脚本交接、WAV、QA 和真实确认文字。

Chatterbox 会写入隐式合成音频水印；不得移除或规避。发布时还要按平台要求主动声明 AI 合成。
