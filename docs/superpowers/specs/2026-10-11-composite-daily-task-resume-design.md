# 复合日常任务按子任务续跑设计

## 目标

给多步骤日常编排增加统一的 `--from-task TASK` 参数。用户可以指定一个业务子任务，跳过它之前的业务子任务，并从所选任务继续执行该编排的剩余部分。每日总流程支持跨阶段的完整任务 ID；可独立运行的复合命令支持本命令范围内的任务 ID。

## 命令契约

- `daily-rewards --from-task ID` 接受带阶段前缀的稳定任务 ID，例如 `legion.shop_purchases` 或 `base.element_trial`。所选任务及其后续任务按每日总流程顺序执行；此前的任务在摘要中标为 `skipped`。
- `daily-rewards --from-step N` 保持现有八阶段行为和兼容性。它与 `--from-task` 互斥；未传两者时仍从完整流程开始。
- 每个可独立运行的多子任务编排也接受 `--from-task ID`，其中 ID 在本命令内唯一，例如 `legion-daily-rewards --from-task shop` 或 `journey-daily-rewards --from-task purifier`。它执行所选任务和同一编排的后续任务。
- 每个 selector 都只在业务任务边界生效，不恢复任务内部的某个点击，也不从某个重复循环的中间一轮续跑。选中重复批次时会从第一轮按原配置完整执行；若该批次已部分执行，应从后续业务任务续跑，不要再次选择该批次。
- 未知 ID、`--from-task` 与 `--from-step` 冲突，或当前命令不支持 selector 时，必须在发送任何点击前报错。

## 每日总流程任务 ID

| ID | 任务 |
| --- | --- |
| `patrol.claim` | 打开巡逻并领取巡逻收益 |
| `patrol.quick_patrol` | 普通快速巡逻批次 |
| `patrol.ad_patrol` | 广告快速巡逻批次 |
| `calendar` | 日历免费奖励 |
| `welfare` | 福利免费奖励 |
| `mail` | 邮件奖励 |
| `legion.daily_cut` | 军团每日一刀 |
| `legion.foreign_rewards` | 异域挑战扫荡和奖励领取 |
| `legion.shop_purchases` | 军团商店购买 |
| `legion.journey_gifts` | 征途礼物和征途后续流程 |
| `journey.resources` | 征途金币、木材领取 |
| `journey.purifier` | 净化者招募 |
| `base.cafeteria` | 基地食堂奖励 |
| `base.global_rescue` | 寰球救援 |
| `base.deep_abyss` | 深渊挑战 |
| `base.terminal_crisis` | 终末危机 |
| `base.battlefield_contest` | 战场争霸 |
| `base.element_trial` | 元素试炼 |
| `base.play_shop` | 训练大厅玩法商店 |
| `shop.resource_gold` | 商城资源页免费金币 |
| `shop.special_pack_gold` | 商城特惠礼包免费金币 |

## 独立复合命令

相同任务边界在单独运行时使用本地 ID：

- `patrol-full-from-home`: `claim`, `quick_patrol`, `ad_patrol`
- `legion-daily-rewards`: `daily_cut`, `foreign_rewards`, `shop`, `journey_gifts`
- `journey-daily-rewards`: `resources`, `purifier`
- `base-training-hall`: `cafeteria`, `global_rescue`, `deep_abyss`, `terminal_crisis`, `battlefield_contest`, `element_trial`, `play_shop`
- `shop-training-hall`: `resource_gold`, `special_pack_gold`
- `legion-reward-claims`: `sweeps`, `legion_rewards`, `personal_rewards`
- `legion-shop-purchases`: `gun_blueprint`, `base_powder`, `enhancer`
- `legion-journey-gifts`: `gift_claim`, `expedition`
- `base-training-hall-shop`: `base_powder`, `gun_blueprint`, `base_materials`, `skill_manual`

只包含一个业务任务的命令，以及重复执行同一种操作的批量命令，仍视为原子任务；现有次数参数继续控制批量大小。

## 页面与安全边界

每次运行仍执行既有游戏窗口聚焦、几何校验和校准。使用 `--from-task` 时，用户需先将游戏停在所选业务任务的已知入口页面；帮助和任务计划输出需说明该页面前置条件。程序不读取或推断游戏内页面，不保存上次进度，也不自动重放前序导航。

`--dry-run` 输出完整任务顺序、被跳过项、开始任务和后续任务，不发送点击、拖动或等待。参数校验应发生在任务的点击执行之前。此前已发生的任务仍由用户判断是否成功；续跑不把“曾经启动过”当作完成证据。

## 实现方向

每个复合编排以稳定 ID 标记可续跑的业务子任务，并由共享 selector 逻辑验证 ID、切出待执行后缀、渲染跳过与待执行摘要。各命令保留现有点击封装、顺序、业务等待、窗口边界和失败恢复。每日总流程将所选的阶段内任务传给对应编排，并在该子任务完成后继续后续日常阶段。

实现前检查所有调用点、参数转发和 dry-run 路径；不改坐标或业务动作。验证需覆盖 selector 的合法/非法输入、任务后缀和跳过摘要、默认完整顺序，以及嵌套每日流程的任务转发。模拟 dry-run 仅证明计划生成，不证明游戏页面或奖励状态。
