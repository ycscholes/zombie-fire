# 征途净化者免费招募设计

## 目标

在征途模块新增独立的 `journey-purifier-recruit` 命令：进入征途、打开净化者列表、点击已确认免费的招募按钮、拖动招募者列表使六名招募者完整可见，并依次领取六个头顶按钮的奖励。每次领取后关闭对应的奖励弹窗。该任务也纳入 `daily-rewards` 的第 6 个征途阶段，在既有金、木资源领取后执行。

## 范围与接口

- 保留 `journey-resource-claim` 的现有金、木领取行为和 CLI 接口不变。
- 新增 CLI 命令：`python3 scripts/zombie_click.py journey-purifier-recruit`。
- 新增内部征途组合处理器，顺序执行资源领取和净化者招募；`daily-rewards` 的第 6 阶段改为调用该组合处理器。
- 仅处理用户已确认“完全免费”的招募与六个头顶奖励按钮。不点击钻石、道具、广告、付费或文案/费用不明确的控件。

## 实现边界

- 在 `scripts/zombie_actions.py` 登记净化者入口、招募、列表拖动起终点、六个领取点和奖励弹窗关闭点；全部使用 508x949 窗口本地坐标。
- `scripts/zombie_tasks/journey.py` 负责流程编排；点击、拖动、窗口校验、日志和投递重试只能使用 `zombie_common.py` 的共享入口。
- 执行顺序为：`journey_tab` → `journey_purifier_entry` → `journey_purifier_recruit` → `journey_purifier_list_drag` → 六组 `journey_purifier_claim_N` → `journey_purifier_reward_dismiss`。
- 每个领取点经 `perform_reward_click()` 触发，以维持领取后最小输入间隔；关闭动作经 `perform_dismiss_click()` 执行。
- 任一窗口/几何校验失败、真实输入投递失败或奖励页面异常时立即停止，不尝试后续角色或猜测替代坐标。共享层对一次投递失败的既有重试保持不变。
- `--dry-run` 必须输出全部命名点及拖动计划，且不得聚焦、点击、拖动或等待。

## 校准与验收

- 在真实招募者列表完成一次拖动后，读取六个头顶领取按钮和奖励弹窗关闭点的实际位置；这些点在写入动作表前须确认对应免费奖励。
- 单元测试覆盖 CLI 注册、独立命令的入口/招募/拖动/六次领取和六次关闭顺序、`perform_reward_click()` 的六次调用、dry-run 零输入，以及日常第 6 阶段先资源后净化者的组合顺序。
- 运行全量 `unittest`、Python 编译、`--mock-bounds 2,33,508,949 journey-purifier-recruit --dry-run`、`daily-rewards --dry-run` 和 `git diff --check`。
- mock dry-run 只证明调度和坐标映射；真实完成只以六次可见奖励弹窗及其关闭后的游戏状态为准。
