# 操作日志统一设计

## 目标

让自动化每一次实际输入操作都有一条立即输出、可追溯的日志；覆盖普通点击、弹窗关闭点击和 CoreGraphics 拖拽，同时不改变既有点击节奏、坐标映射或安全检查。

## 现状

`scripts/zombie_common.py` 是所有任务模块的输入安全边界：`perform_click` 在聚焦、窗口校验后调用后端，`perform_dismiss_click` 委托普通点击。任务模块自行打印业务日志，因此部分直接调用的购买按钮没有逐次记录。拖拽直接调用 `drag_cgclick_bin`，也没有统一日志。

## 方案

Every human-readable console log line begins with the current local time in `HH:MM` form, for example `01:11 base training hall: training_hall_back (clicked) via cgclick`. Prefix each line independently when a message spans multiple lines. Keep machine-readable JSON output free of the prefix.

在公共模块添加一个小型 `log_operation` 函数。它向标准输出写入固定格式的 `operation:` 日志，包含操作种类、屏幕坐标、后端与状态；每次成功点击在后端选定后记录一次。点击失败前也记录失败状态和错误原因，然后保持原有异常语义。

将拖拽收敛到 `perform_drag`：它复用每次输入前已有的聚焦与窗口不变检查，再调用 `drag_cgclick_bin`。成功时记录起止坐标和 `cgclick` 后端；不可用时记录失败并抛出原有 `ClickDeliveryError`。任务模块改为调用该入口，不能再绕过它。

现有任务级业务日志继续保留，作为“为什么点”的语义补充；`operation:` 日志负责“实际执行了什么”。不为无输入的等待、状态读取或 dry-run 产生日志。

## 验收与测试

- 任意 `perform_click` 成功输出一条包含点击坐标、后端和成功状态的 `operation:` 日志。
- 点击后端不可用时，在抛出异常前输出一条失败日志。
- 任意 `perform_drag` 成功或失败各输出一条日志，并保持聚焦/窗口校验顺序。
- 所有任务的可读控制台日志及输入操作日志均以本地 `HH:MM` 时间前缀开头；JSON 输出保持原格式。
- 福利、训练场/商城和军团路径的拖拽全部通过 `perform_drag`。
- 既有完整单元测试与 dry-run 不引入真实输入。
