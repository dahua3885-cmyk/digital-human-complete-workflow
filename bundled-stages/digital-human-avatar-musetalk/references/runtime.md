# MuseTalk 1.5 运行环境

## 固定上游

- 官方仓库：`https://github.com/TMElyralab/MuseTalk`
- 固定提交：`0a89dec45a0192b824e3cf4daf96c239440c5ed8`
- 官方建议：Python 3.10、CUDA 环境、FFmpeg；MuseTalk 1.5 使用 `models/musetalkV15/unet.pth` 与 `models/musetalkV15/musetalk.json`。

上游代码采用 MIT License。官方 README 说明 MuseTalk 训练模型可用于包括商业用途在内的用途；其他依赖模型仍分别遵守各自许可证，官方测试数据只允许非商业研究，不能随本 Skill 作为商业演示素材分发。

## 默认本地位置

运行配置默认保存在：

`<CODEX_HOME>/runtimes/digital-human-avatar-musetalk/runtime.json`

其中只记录本机 MuseTalk 仓库、Python、FFmpeg 和 FFprobe 路径，不记录声音、肖像、参考视频或密钥。

## 兼容边界

- 官方主要支持 Windows 与 Linux 的 NVIDIA CUDA 环境。
- 没有 NVIDIA GPU、显存不足、缺 Python 3.10 或模型下载不完整时，不能把本地 MuseTalk 标记为可运行。
- 官方公开的最低测试信息包括 Windows + RTX 3050 Ti Laptop 4GB、FP16、8 秒视频约 5 分钟；这不是所有机器的速度保证。
- macOS 与纯 CPU 不属于本发行版验证过的本地生成环境，不能宣称兼容。

## 隐私

所有真人声音、肖像和视频保存在使用者自己的工作区或私有目录。安装脚本只下载公开代码与模型，不把身份素材上传给维护者。
