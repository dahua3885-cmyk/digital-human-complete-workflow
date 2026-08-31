# 第三方组件与公开模型

本阶段直接随包提供 MuseTalk 推理源码，固定到官方提交：

- 项目：`TMElyralab/MuseTalk`
- 提交：`0a89dec45a0192b824e3cf4daf96c239440c5ed8`
- 代码许可证：MIT
- 原始许可证：`vendor/MuseTalk/LICENSE`

模型权重不直接提交进本仓库。`scripts/download_public_models.py` 根据 `assets/public-models.json` 从 Hugging Face 的固定 revision 下载 MuseTalk 1.5、SD VAE、Whisper 与 face-parse-bisent 文件。下载器会保存来源、revision、字节数和 SHA-256。

`overlays/portable-inference/` 是本项目在固定上游源码之上的公开兼容层：修正包内导入、适配当前 PyTorch 的可信权重加载，并在固定机位正面口播路线中使用人脸检测框，避免 Windows 必须编译可选的 mmcv/mmpose 扩展。补丁文件、用途和树哈希记录在 `overlays/manifest.json`，不包含任何人物数据。

公开包明确排除：上游测试音视频和演示图片、任何用户声音或肖像、身份文件、Cookie、令牌、作者本机路径以及生成结果。

各模型和依赖继续遵守各自许可证。把本项目用于商业内容前，使用者仍需核对其实际使用版本的许可证和素材授权；Apache-2.0 只覆盖本项目自己的编排与安装代码，不改变第三方许可证。
