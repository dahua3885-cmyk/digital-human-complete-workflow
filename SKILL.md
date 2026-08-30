# 数字人完整流程 Skill

这是一个面向 Codex 的数字人视频流程编排 Skill，支持把以下四个阶段串联起来，也支持分别调用其中任一模块：

`二创文案 → 数字人音频 → 数字人画面 → 剪辑包装`

当前版本为 **0.9.3-draft 公开预览版**。仓库提供流程路由、首次建档、数字人资产中心、任务订单、阶段确认、路径与哈希交接、授权与安全规则、安装和发行校验；不附带四个通用阶段执行器、模型权重、第三方服务、人物声音或肖像素材。因此，它是可安装的编排层，不是无需配置即可生成成片的一键模型包。

## 一、可以怎样使用

### 完整流程

提供一个视频链接或源视频后，依次完成：

1. 二创文案并由用户确认；
2. 生成数字人音频并由用户试听确认；
3. 生成数字人画面并由用户确认；
4. 完成剪辑包装和封面。

### 分别制作

- **二创文案**：提供视频链接、视频文件、转写稿或原始文案。
- **数字人制作**：提供确认后的文案，依次生成音频和数字人画面。
- **剪辑包装**：直接提供现成的数字人口播视频进行包装。

模块完成后可继续下一阶段，系统通过任务订单传递已确认文件的路径、版本和 SHA-256，不需要手工复制粘贴中间文案。

## 二、安装

将本仓库克隆或下载到 Codex 的 Skills 目录，并保持目录名为 `digital-human-complete-workflow`。

```powershell
git clone https://github.com/dahua3885-cmyk/digital-human-complete-workflow.git "$env:CODEX_HOME\skills\digital-human-complete-workflow"
cd "$env:CODEX_HOME\skills\digital-human-complete-workflow"
python scripts/verify_distribution.py .
```

如果没有设置 `CODEX_HOME`，通常可安装到用户目录下的 `.codex/skills/digital-human-complete-workflow`。只有校验输出 `DISTRIBUTION_OK`，才说明下载包内部完整。

把下面这段固定话术直接发给需要安装的 Codex。必须保留“安装并立即启用”，不得缩写成只有“安装”：

```text
请安装并立即启用这个 GitHub 仓库根目录中的 Skill，安装名称为 digital-human-complete-workflow：

https://github.com/dahua3885-cmyk/digital-human-complete-workflow
```

同一话术也单独保存在[安装话术](安装话术.md)，方便直接复制。安装与首次启用必须在这一条请求中连续完成，不要求用户安装后再发送第二句话。

首次调用时，Skill 会把最新版客户文档复制到当前 Codex 活动工作区；Codex Desktop 支持文件打开能力时会主动打开两个本地副本，同时欢迎语保留两个 GitHub 在线备用链接。这样不把单一文件查看器或单一操作系统当成唯一入口：

- [数字人完整流程使用手册](数字人完整流程.md)
- [开始使用前请先填写](开始使用前请先填写.md)

用户只需选择简洁版或专业版填写一次，并按照文档末尾提示复制全文发回 Codex。资料完整后，不应再重复索要第二套资料。

## 三、兼容性验证

仓库通过 GitHub Actions 在 Windows、macOS 和 Ubuntu、Python 3.11/3.12 上验证发行完整性、中文与空格工作区、两份文档复制、在线备用链接和用户修改保护。自动测试能证明这些文件与脚本行为，但不能证明所有 Codex 客户端版本的界面都完全相同；未在支持矩阵中验证的环境应视为实验性。

## 四、接入实际生成能力

1. 将 [运行配置示例](assets/runtime-config.example.json) 复制到仓库之外的私有工作区，命名为 `runtime-config.json`。
2. 为二创、音频、画面和包装四个阶段填写实际 Skill、命令、模型或服务检查项。
3. 各阶段适配器须符合[阶段适配器合同](references/stage-adapter-contract.md)。
4. 运行预检：

   ```powershell
   python scripts/preflight_runtime.py <私有runtime-config.json>
   ```

只有输出 `END_TO_END_READY` 时，才表示当前电脑具备完整流程的实际运行条件。详细步骤见[下载、安装与可运行验收](references/installation-and-runtime.md)。

## 五、隐私、授权与合成内容

- 本项目默认本地运行，维护者不接收或托管使用者的声音、肖像、证件、客户素材和生成结果。
- 只能使用本人素材，或已经取得可验证授权的第三方声音与肖像；公开视频或一张照片不等于授权。
- 使用者负责确保输入、用途、生成、发布和传播合法，并按适用法律及平台规则保留生成合成标识。
- 不要在公开 Issue、仓库或日志中提交真人母片、密钥、身份证件、客户数据或违法内容原件。
- 对诈骗、冒用、侵权、规避合成标识等用途，维护者可以拒绝提供针对性支持。

具体边界见[开源维护者责任边界与滥用处理](references/maintainer-liability-and-abuse.md)与[授权、隐私与标识](references/consent-and-disclosure.md)。这些资料是产品安全建议，不替代专业法律意见。

## 六、开源范围与许可证

本仓库内的代码和文档采用 [Apache License 2.0](LICENSE)。该许可证不授权任何人的声音、肖像、姓名、签名、账号品牌或商标；仓库也不包含这些资产。第三方模型、服务、素材和阶段 Skill 仍受各自许可证及服务条款约束。

当前已知限制和正式版条件见[当前阶段依赖审计](references/current-stage-dependency-audit.md)与[发行检查清单](references/release-checklist.md)。欢迎阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 后提交改进。
