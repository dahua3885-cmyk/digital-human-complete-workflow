# 四阶段公共运行能力审计

审计日期：2026-09-01。原有大华专用四个 Skill 未修改，本仓库另建去个人化的公共阶段。

## 结论

0.9.8 已随包提供四个默认阶段 Skill、确定性的运行检查、安装器和真实交接合同。默认 Profile 不含 `your-*`、`replace-*` 或示例阶段。安装 Skill 不等于大型模型已经下载；创建任务前必须按本次所需阶段运行真实预检。

## 四个公共阶段

- 二创：`digital-human-rewrite-generic`，使用 Codex 原生研究与改写能力，生成来源、文案、QA 和批准交接物。
- 数字人音频：`digital-human-voice-chatterbox`，固定 Chatterbox 0.1.7、固定公开模型 revision 和 Perth 水印依赖；参考声和生成音频只保存在用户本机。
- 数字人画面：`digital-human-avatar-musetalk`，随包提供固定 MuseTalk 1.5 源码与完整性校验，公开模型按需下载；需要兼容 NVIDIA CUDA 环境。
- 剪辑包装：`digital-human-packaging-fixed`，使用 FFmpeg、Pillow 与固定开源中文字体，输出竖屏母版、带封面发布版和三种封面。

## 仍由使用者提供

- 有合法授权的参考声、肖像视频、原始内容和发布用途。
- 足够磁盘空间、网络、FFmpeg，以及画面阶段所需 NVIDIA GPU/CUDA。
- 首次声音与画面阶段的大型公开模型下载同意。

## 不得误导的边界

- 发行校验通过只证明安装包内部完整。
- 阶段 `check_runtime.py` 通过才证明该电脑上的对应阶段可运行。
- 四阶段预检和演示任务均通过后，才可以说该电脑能完成端到端生成。
- 缺环境时应给出中文缺口和修复动作，不能再说“请另找一个真实 Skill”。
