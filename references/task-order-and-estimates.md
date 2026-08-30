# 任务订单、预计时间与版本更新

## 每次开始都先建订单

不论用户只做一个模块还是完整流程，都先创建 `task-order.json`：

```powershell
python scripts/create_task_order.py <工作区> --project <slug> --entry <阶段> --target <阶段> --source-kind <url|file|text> --source <值>
```

`entry` 决定从哪里开始，`target` 决定本次先做到哪里。四个阶段顺序固定为 `rewrite → voice → avatar → packaging`，不能倒序。

## 每个阶段之前怎样显示预计时间

用户界面只显示一个容易理解的大致区间，例如“二创预计约 15–25 分钟”或“数字人画面预计约 20–35 分钟”，不展示模型、显卡、倍率和复杂计算。默认不包含用户等待确认的时间。

内部订单仍可保存估算依据，方便维护者校准；若暂时无法估算，显示“检测环境后给出时间”，不得编造数字。

只有写入估时后才能把阶段改成 `running`：

```powershell
python scripts/update_task_order.py <task-order.json> start --stage voice --estimate-low 8 --estimate-high 15 --basis "180秒文案；本机近5次同模型记录"
```

完整流程可以显示剩余阶段总区间，但三个用户确认点只标记“等待确认”，不计算等待时长。

## 失败怎样记录

技术层仍记录具体原因，但用户界面按情况简化：

- 网络不可用：显示“网络异常，恢复网络后继续”，禁用生成按钮，不显示“生成失败”。
- 已生成但效果没有达到预期：显示“待优化”，进入对应反馈文件，不称文件损坏。
- 模型或服务明确报错：显示该阶段暂未完成和可理解的原因；恢复条件满足后再继续。

内部记录仍可包含当前阶段、已保留制品和重试时间：

```powershell
python scripts/update_task_order.py <task-order.json> fail --stage avatar --reason "参考视频在12.4秒出现遮嘴，嘴部驱动体检拒收" --retry-low 6 --retry-high 10 --basis "重录片段后重新跑素材体检和8秒样片"
```

下一次重试前仍要把新增时间展示给用户。

## 为什么不是“文件失效”

用户修改文案后，旧 WAV、旧数字人 MP4 和旧包装视频通常仍然可以播放，它们没有损坏。正确状态是：

- 旧制品：保留为 `historical`，仍可查看和追溯。
- 当前订单：从变化发生的阶段开始标记 `needs_update`。
- 原确认：继续保存，但只绑定旧文件哈希，不能自动批准新版本。
- 新阶段：重新生成后产生新哈希和新确认。

```powershell
python scripts/update_task_order.py <task-order.json> needs-update --from-stage rewrite --reason "用户修改了最终口播稿"
```

这里的“需更新”只是版本一致性要求，不表示旧文件技术损坏，也不表示严格执行仍会失败。

## 阶段完成怎样自动进入下一模块

阶段完成后登记交接物：

```powershell
python scripts/update_task_order.py <task-order.json> complete --stage rewrite --handoff <script-handoff.json>
```

脚本计算交接物 SHA-256，把下一阶段设为 `ready`，并把同一个交接引用写成下一阶段输入。它不会要求用户复制粘贴，也不会自动跨越文案、音频和画面确认。
