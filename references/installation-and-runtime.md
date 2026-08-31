# 下载、安装与可运行验收

## 唯一官方安装话术

对外分享时逐字发送以下内容，不增加安装脚本说明，也不拆成第二条启用消息：

```text
请安装并立即启用这个 GitHub 仓库根目录中的 Skill，安装名称为 digital-human-complete-workflow：

https://github.com/dahua3885-cmyk/digital-human-complete-workflow
```

这段话同时触发安装和第一次启用。只有“安装”而没有“立即启用”时，标准安装流程可能在提示“下一轮可用”后停止，无法在同一条请求中执行欢迎语和两份文档交付。

## 两种“完整”不能混淆

- **发行包完整**：总控 Skill 的说明、模板、脚本、配置和引用文件没有缺失或损坏。
- **端到端可运行**：发行包完整，并且四个阶段 Skill、模型/服务、命令、授权素材和硬件都已配置，通过运行预检和演示任务。

本 Skill 可以用脚本保证第一项，并在 0.9.6 起随包安装 `digital-human-avatar-musetalk` 画面阶段。第二项仍取决于其余阶段实现、MuseTalk 模型与 CUDA 环境、用户选择的声音/包装运行时、服务授权和硬件；缺任一项都不能宣称“一下载就能完整运行”。

这些是维护者和生产阶段的技术边界。首次客户启用时只执行 `SKILL.md` 的固定三段欢迎协议，不向客户展示版本号、发行校验、工作区状态、运行配置或端到端状态。只有用户实际发起某个生产阶段且该阶段预检不通过时，才说明与当前请求直接相关的缺口。

## GitHub 下载后的固定顺序

1. 解压或克隆仓库，保持 `digital-human-complete-workflow/` 目录结构不变。
2. 运行内部完整性校验：

   ```powershell
   python scripts/verify_distribution.py .
   ```

   只有出现 `DISTRIBUTION_OK` 才表示关键文件、JSON、Python语法和本地引用完整。

3. 静默运行 `python scripts/install_bundled_stage_skills.py`，确认 `digital-human-avatar-musetalk` 已安装到同一 Codex Skills 目录；旧工作区再运行 `migrate_stage_bindings.py`。然后把 `assets/runtime-config.example.json` 复制到用户私有工作区，命名为 `runtime-config.json`。不要在公开仓库里填写模型路径、密钥和真人素材路径。
4. 为四个阶段填写实际 `skill_name`、`skill_root` 和 provider/model/runtime 检查。每个阶段都必须符合 [阶段适配器合同](stage-adapter-contract.md)。
5. 运行运行时预检：

   ```powershell
   python scripts/preflight_runtime.py <私有runtime-config.json>
   ```

   只有出现 `END_TO_END_READY` 才允许完整流程入口；某一模块未就绪时只开放不依赖它的入口。

6. 初始化本地用户工作区：

   ```powershell
   python scripts/init_user_workspace.py <用户工作区> --modules all --creator-profile quick
   ```

   初始化会建立 `profiles/asset-center.json`、四类 Profile 位置和项目订单目录，不会上传真人素材。

7. 用 `create_task_order.py` 建立一个演示订单，验证单模块完成后可以用 `update_task_order.py ... extend` 继续下一模块，且交接路径和哈希自动传递。
8. 用无真人隐私的演示项目跑通所需入口，再开始真实项目。

## 运行配置检查类型

`runtime-config.json` 的每个阶段可声明：

- `command`：命令能否被当前环境找到，例如 `ffmpeg`。
- `path`：模型、仓库、配置或运行时路径是否存在。
- `env`：API型提供商所需环境变量是否已设置；预检只检查存在，不输出密钥值。
- `python_module`：当前 Python 能否发现所需模块。

`readiness_attested` 只能在阶段 Skill 自身安装说明、许可证和provider检查都完成后设为 `true`。它不是跳过检查的开关；所有列出的检查仍必须通过。

## 发行仓库要真正做到一键运行还必须包含

- 所有通用阶段 Skill，或可复现、固定版本、带校验值的安装源；0.9.6 已满足数字人画面阶段这一项。
- 阶段适配器能力和交接物合同。
- Python/Node/ffmpeg 等运行环境的版本与安装方式。
- 模型或服务提供商的获得方式、许可证、所需显存/网络和配置方式；不能把不可再分发权重偷偷塞进仓库。
- 一套可合法再分发的演示输入、预期输出清单和通过记录。
- Windows、GPU和提供商兼容性矩阵。

## 发布阻断

以下任一存在时，只能称“编排草案”或“发行候选”，不能称完整可运行版：

- Profile 中本次要启用的阶段仍是 `your-*` 或 `replace-*` 示例绑定；默认数字人画面阶段不允许再出现此情况。
- 四个阶段 Skill 只有作者本机路径，没有公共安装源。
- 模型/服务、ffmpeg、运行时或关键脚本未通过预检。
- 阶段 Skill 包含个人参考声、肖像、密钥或作者机器绝对路径。
- 没有端到端演示通过记录。
