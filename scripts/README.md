# Script layout

`zombie_click.py` is the only CLI entry point. `zombie_common.py` owns the
shared safety boundary and input primitives, while `zombie_actions.py` owns
the calibrated action registry. Page-specific commands are split into
`zombie_tasks/{patrol,home,legion,journey,base,shop,daily}.py`; shared named
task IDs and suffix selection live in `zombie_tasks/resume.py`.

The daily workflow has eight phases; `--from-step 7` starts at base training
hall and `--from-step 8` starts at shop training hall. Use the repository
unittest command from the root for verification.

Use `daily-rewards --from-task legion.shop_purchases` to resume at that
business task and continue through later daily phases. Existing
`daily-rewards --from-step N` remains available and cannot be combined with
`--from-task`. A selected task runs with later tasks in its route; earlier IDs
are reported as skipped and are not checked. The game must already be on the
selected task's entry page. `--dry-run` prints the selector plan without input.

Composite commands accept these local task IDs:

| Command | IDs | Entry page for the selected ID |
| --- | --- | --- |
| `patrol-full-from-home` | `claim`, `quick_patrol`, `ad_patrol` | Home for `claim`; patrol panel for the other two |
| `legion-daily-rewards` | `daily_cut`, `foreign_rewards`, `shop`, `journey_gifts` | Home for the first two; Legion page for the last two |
| `journey-daily-rewards` | `resources`, `purifier` | Home |
| `base-training-hall` | `cafeteria`, `global_rescue`, `global_expedition`, `deep_abyss`, `terminal_crisis`, `battlefield_contest`, `element_trial`, `play_shop` | Base page for `cafeteria`; training-hall list for the rest. Battlefield Contest and Element Trial auto-scroll to the bottom; `--skip-scroll` requires the list at bottom |
| `shop-training-hall` | `resource_gold`, `special_pack_gold` | Home for `resource_gold`; special-pack shop page for `special_pack_gold` |
| `legion-reward-claims` | `sweeps`, `legion_rewards`, `personal_rewards` | Home; foreign-challenge page; Legion rewards panel, respectively |
| `legion-shop-purchases` | `gun_blueprint`, `base_powder`, `enhancer` | Legion shop list scrolled to the selected item |
| `legion-journey-gifts` | `gift_claim`, `expedition` | Legion page; Journey gift page, respectively |
| `base-training-hall-shop` | `base_powder`, `gun_blueprint`, `base_materials` | Play shop at the selected item |

The CLI help and resume plan show the required entry page for each selected ID.
The daily IDs are `patrol.claim`, `patrol.quick_patrol`, `patrol.ad_patrol`,
`calendar`, `welfare`, `mail`, `legion.daily_cut`, `legion.foreign_rewards`,
`legion.shop_purchases`, `legion.journey_gifts`, `journey.resources`,
`journey.purifier`, `base.cafeteria`, `base.global_rescue`,
`base.global_expedition`, `base.deep_abyss`, `base.terminal_crisis`, `base.battlefield_contest`,
`base.element_trial`, `base.play_shop`, `shop.resource_gold`, and
`shop.special_pack_gold`. For example, local selectors include
`legion-daily-rewards --from-task shop` and
`base-training-hall --from-task element_trial`. A repeated task starts at its
first iteration with the configured count; it cannot resume midway through a
batch. The temporarily disabled play-shop skill-manual purchase has no task ID.

`journey-purifier-recruit` is the standalone free-only purifier task. It clicks
the current all-evolver 招募 button once without dragging or individually
claiming recruiter buttons. It is also included in the Journey phase of
`daily-rewards`, after the gold and wood resource claims.

`base-training-hall` runs the base route in order: cafeteria claim, Global
Rescue free reward, Global Expedition free reward, Deep Abyss challenge/fail
plus two sweeps, Terminal Crisis free sweep, then the existing Battlefield
Contest and Element Trial tasks. It returns to the base page when complete.
`base-training-hall-deep-abyss` runs only the Deep Abyss subtask; start it from
the training-hall list page. It returns to the training hall when complete.
`base-training-hall-global-rescue` claims the visible free reward and returns
to the training-hall list. `base-training-hall-global-expedition` does the
same for the Global Expedition free reward. `base-training-hall-terminal-crisis`,
`base-training-hall-battlefield-contest`, and
`base-training-hall-element-trial` run those routes independently. Each starts
from the open training-hall list and returns there. Battlefield Contest accepts
`--battle-times` (default `5`). These commands reuse the composite route's
actions; Terminal Crisis, Battlefield Contest, and Element Trial scroll to the
bottom when needed. They do not replenish attempts or add purchase/ad actions.
`base-training-hall-shop` starts from the already-open training hall and runs
the enabled play-shop purchases: base powder, gun blueprint, and base materials.

## Coordinate mapping

Computer Use coordinates are window-local coordinates from the game screenshot.
The `Action` registry uses the same canonical `508x949` window-local space.
CoreGraphics uses global screen coordinates, so `scale_point()` adds the
calibrated window origin once:

```text
screen_x = bounds.x + round(action.x * bounds.width / 508)
screen_y = bounds.y + round(action.y * bounds.height / 949)
```

With `bounds=(2,33,508,949)`, Computer Use `(358,513)` therefore becomes
`Action(358,513)` and CoreGraphics `(360,546)`. Do not add a title-bar offset
to the action coordinate yourself; inspect the conversion with `dry-run`.

### 任务组合规则

模块总任务优先调用已有子任务，不复制子任务的点击、领奖和等待循环。
军团每日任务按“每日一刀 → 异域挑战领奖 → 商店 → 征途赠礼”组合；
异域挑战领奖复用 `command_legion_sweep_batch`，首页广告巡逻复用
`command_patrol_ads_batch`。组合调用传入已校准窗口，清空子任务的续跑参数，
保留共享阶段进度，子任务失败向上抛出。

完整巡逻保留独立的普通和广告循环，因为其奖励关闭等待和广告返回游戏检查
与独立批次不同；不得为复用而省略这些检查或改变等待时间。
