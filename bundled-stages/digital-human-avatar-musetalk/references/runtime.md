# MuseTalk 1.5 运行环境

## 固定上游

- 官方仓库：`https://github.com/TMElyralab/MuseTalk`
- 固定提交：`0a89dec45a0192b824e3cf4daf96c239440c5ed8`
- 官方建议：Python 3.10、CUDA 环境、FFmpeg；MuseTalk 1.5 使用 `models/musetalkV15/unet.pth` 与 `models/musetalkV15/musetalk.json`。

发行包已经直接包含该固定提交的推理源码、许可证、依赖清单与源码树 SHA-256，不依赖用户另外克隆 Git 仓库。为提高 Windows 首次运行成功率，另带经过实际渲染验证的便携推理补丁层，并以独立清单和哈希与原始上游源码区分。官方测试音视频、演示图片和模型权重没有随包复制。

上游代码采用 MIT License。官方 README 说明 MuseTalk 训练模型可用于包括商业用途在内的用途；其他依赖模型仍分别遵守各自许可证，官方测试数据只允许非商业研究，不能随本 Skill 作为商业演示素材分发。

## 首次准备

`setup_runtime.py` 会依次完成：

1. 校验随包 MuseTalk 源码树；
2. 复制公开引擎到使用者本机 Codex runtime 目录；
3. 建立 Python 3.10 专用虚拟环境并安装锁定依赖；
4. 从 `assets/public-models.json` 中固定的 Hugging Face revision 下载公开模型；
5. 记录每个模型文件的来源、revision、字节数和 SHA-256；
6. 写入本机 `runtime.json` 并交给 `check_runtime.py --deep` 验收。

Windows 缺 Python 3.10 或 FFmpeg 时，只有用户明确同意 `--accept-system-changes` 才通过 winget 安装；NVIDIA 驱动不由 Skill 擅自更新。

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
