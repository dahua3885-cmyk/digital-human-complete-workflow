---
name: digital-human-avatar-musetalk
description: Generate an authorized mouth-only digital-human MP4 from a user-approved audio file and a user-authorized single-person reference video using a locally configured MuseTalk 1.5 runtime. Use for 数字人画面、数字人口型、确认音频后生成数字人视频. Do not generate or alter voice audio.
metadata:
  version: "0.1.0"
---

# 通用数字人画面｜MuseTalk 1.5

本 Skill 只负责：

`已确认音频 + 已授权人物参考视频 → MuseTalk 1.5 嘴部口型 → 完整 MP4 → 技术与人工 QA`

它不生成声音，不修改已经确认的音频，也不包含任何人的参考视频、肖像或模型私有路径。

## 开工前

1. 确认用户对声音、肖像、参考视频和本次发布用途拥有合法权利；第三方人物需要可验证授权。
2. 确认音频已经由用户试听并明确批准，记录文件 SHA-256；画面阶段不得重做或修改音频。
3. 读取总控提供的录制检查清单，对参考视频进行单人、固定机位、脸部和嘴部无遮挡、无硬切、背景与光线稳定检查。
4. 静默运行：

   ```powershell
   python scripts/check_runtime.py --json
   ```

   只有返回 `ready: true` 才能开始渲染。未就绪时不得再说“阶段绑定还是示例 Skill”；应根据 `problems_zh` 用中文说明当前电脑缺少的实际运行条件。
5. 首次需要本地安装 MuseTalk 时，先告诉用户将下载数 GB 模型、需要 NVIDIA GPU、Windows/Linux、FFmpeg 和 Python 3.10；用户明确同意后才运行：

   ```powershell
   python scripts/setup_runtime.py --accept-large-download
   ```

   已有可运行的 MuseTalk 1.5 环境时，使用 `--register-existing-repo` 和 `--register-existing-python` 登记，不重复下载。

## 生成

先在当前项目 `work/` 中建立代表性内部样片，使用：

```powershell
python scripts/render_musetalk.py `
  --video <授权参考视频> `
  --audio <已确认音频> `
  --output <输出MP4>
```

脚本会在系统临时目录使用 ASCII 中间路径，避免中文路径导致 OpenCV/FFmpeg 失败；最终文件仍写入用户当前 Codex 工作区，不写回源素材目录。

## 质量闸门

- 只采用 MuseTalk 1.5 的嘴部口型路线，不用整脸、整头或身份替换兜底。
- 参考视频不是越长越好；最低 30 秒，推荐 60–90 秒连续稳定单人素材。
- 动态背景、多人、运镜、遮嘴、强烈转头、失焦、曝光跳变或硬切不得直接进入正式生成。
- 完整制作前必须有内部代表性样片，检查口型、嘴部边缘、脸部身份保持、抖动和首尾帧。
- 最终 MP4 必须含 H.264 视频和 AAC 音频，音画时长差不得超过 0.10 秒。
- 用户观看完整数字人画面并明确确认后，才允许生成画面交接物并进入剪辑包装。

## 输出

- 完整数字人 MP4。
- 输入音频与参考视频 SHA-256。
- MuseTalk 版本、运行配置摘要和输出 SHA-256。
- 技术 QA 结果与人工观看结论。

MuseTalk 官方代码与模型来源、安装要求和许可证见 [运行环境说明](references/runtime.md)。
