---
name: zombie-fire-daily
description: Operate the macOS WeChat mini game 向僵尸开炮 daily routine with low-token calibrated local clicks plus Computer Use verification. Use when Codex should claim free red-dot rewards, patrol income, normal or ad-based 快速巡逻, 日历/邮件/通行证/福利/军团/商城 rewards, or repeat the game's daily chores while avoiding paid or ambiguous actions.
---

# 向僵尸开炮日常

Use `computer-use` for startup verification, risk checks, ad completion checks,
and recovery. Use the bundled fixed-click helper for known safe, repeated
actions:

```bash
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py list
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py state
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py bounds --fit
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py dry-run click reward_dismiss
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py click reward_dismiss
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py patrol-full-from-home
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py --mock-bounds 2,33,508,949 patrol-full-from-home --dry-run
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py daily-rewards
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py daily-rewards --from-step 3
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py --mock-bounds 2,33,508,949 daily-rewards --dry-run
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py mechanical-shock
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py patrol-quick-batch --times 3
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py patrol-ads-batch
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py patrol-ads-from-home --times 5
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py mail-claim
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py calendar-claim
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py welfare-claim
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py base-training-hall
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py legion-sweep-batch --times 2
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py --mock-bounds 0,33,508,949 legion-sweep-batch --times 2 --dry-run
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py legion-reward-claims
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py legion-daily-rewards
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py legion-shop-purchases
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py legion-journey-gifts
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py base-training-hall-deep-abyss
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py base-training-hall-global-rescue
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py base-training-hall-global-expedition
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py base-training-hall-terminal-crisis
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py base-training-hall-battlefield-contest --battle-times 5
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py base-training-hall-element-trial
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py base-training-hall-shop
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py shop-training-hall
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py journey-purifier-recruit
```

The helper maps the normal `508x949` Computer Use coordinate space to the
current front WeChat window. It aborts when the front app, window size, or
aspect ratio does not look like the game window.

### Coordinate mapping (verified on macOS WeChat)

Computer Use screenshot/click coordinates are relative to the captured game
window. `Action` coordinates use that same canonical `508x949` window-local
space. CoreGraphics clicks require global screen coordinates, so the helper
adds the calibrated window origin exactly once:

```text
screen_x = bounds.x + round(action.x * bounds.width / 508)
screen_y = bounds.y + round(action.y * bounds.height / 949)
```

For the fitted window `bounds=(2,33,508,949)`, Computer Use target `(358,513)`
is represented as `Action(358,513)` and delivered to CoreGraphics at
`(360,546)`. Do not manually add the title-bar offset to an `Action` value;
`scale_point()` adds the window origin when producing the final screen point.
Use `dry-run click <action>` to inspect both values before a live click.

Every helper click waits a random `0.8` to `1.0` seconds before the next helper
operation, except the Deep Abyss challenge reward dismissal before `abyss_pause`,
which waits `0.5` seconds. Do not bypass this pacing when adding new scripted
click flows.
Reward-popup dismiss clicks do not add a fixed post-dismiss wait; any needed
transition delay must come from the surrounding business wait.

Every click backend uses the same complete tap semantics: move to the target,
press, hold for 80 ms, then release with click-state `1`. By default, the
helper uses the persistent CoreGraphics `cgclick` helper. The legacy
`--backend system-events` selector is retained for compatibility but delegates
to that same complete CoreGraphics tap because System Events only exposes an
atomic click action.

## Operating Mode

- Treat Computer Use screenshots as expensive. Capture once at startup and once
  before each major surface or risk gate; otherwise use `zombie_click.py` for
  deterministic clicks.
- For patrol-truck-only tasks, do not use Computer Use screenshots at startup,
  during the patrol run, or after completion. Use `bounds --fit` as the shell
  preflight, then `patrol-full-from-home`; count the run as script-attempted
  unless the helper fails closed. Do not use `state` as that shell preflight:
  it observes the current foreground app and can report the terminal instead
  of the game.
- When the user explicitly asks for no screenshots, use only `state`, `bounds`,
  dry-runs, and scripted helper clicks. Do not call Computer Use screenshots for
  that run; fail closed if a step cannot be represented as a known script click.
- Prefer fixed helper actions for harmless, already-known targets: patrol truck,
  patrol claim, quick patrol/ad patrol button, reward dismissal, ad close,
  calendar gift/close, welfare cluster, work-plan sign-in, legion sweep/reward
  claims, shop direct-free gold, top-left back, and top-right close.
- Use `dry-run click <action>` before a new session if the window was moved,
  resized, or opened differently. If the mapped point looks wrong, stop fixed
  clicking and use Computer Use to recover.
- After a fixed click, do not capture just to confirm harmless dismissals.
  Capture only when the next action depends on text, count changes, ad state,
  paid/commercial wording, or an unexpected transition.
- Never infer success from a fixed click alone. Count success only from a
  visible reward popup, an explicit completion state, or a count decrement seen
  at the next required verification point.
- For a standard daily run, prefer this low-token order after the startup gate:
  patrol -> gated 机械震荡 -> battle pass / work-plan sign-in -> gated 武装降临 ->
  gated 拟态牌库 -> calendar -> welfare cluster -> shop inspection -> legion. Capture once per entered surface, then use fixed
  clicks for known free claim buttons and reward dismissal. In legion, capture
  at most once on the legion hub and once on the foreign-challenge page unless a
  verified free reward is already open.
- When a surface has a page-specific bottom-left back button or inner modal
  close, use `back_bottom_left` or `legion_modal_close`; do not retry
  `back_top_left` / `close_top_right` on those surfaces.
- If a helper coordinate misses once on a verified page, use one Computer Use
  recovery click for that session, update the helper coordinate, and stop
  retrying the stale helper point.

## Desktop App Task Plan And Defaults

- The App shows tasks as game tab → module → task. The leaves stay in the real
  `DAILY_TASK_IDS` run order; if the route returns to a prior tab, keep that
  later group in place instead of regrouping tabs and changing execution order.
- The daily page contains run controls and the starting task only. Edit task
  arguments in the single-command view. A shared parameter has one saved value
  used by both its command and the matching daily phase, including status,
  claim count, patrol/legion/base counts, backend, and timing fields. Editing a
  matching command updates what the daily phase receives.
- App command forms default reward-status choices to `available`, animation
  skip choices to `checked`, and task claim counts to `3`. Patrol, legion, base,
  and wait values use the daily composite command's existing defaults; aliases
  show that same default. These are saved form defaults, not observations of
  the current game screen. Before live execution, inspect each gated page in
  Computer Use and update its shared command value when the visible state or
  count differs.
- Direct `zombie_click.py` CLI commands retain their safe gate behavior: an
  omitted status or claim count remains unset and the gated task skips. App
  form defaults do not change the CLI parser defaults.
- The macOS permission notice collapses only when both Accessibility and
  System Events Automation report `granted` without a read error. Unknown,
  denied, timed-out, or failed checks remain visible.

## Safety

- Claim only free rewards.
- Watch ads for patrol-truck `观看广告`. The explicitly authorized 武装降临
  and 拟态牌库 `免费抽取` buttons are the only additional exceptions: use
  each at most once and only when this-run Computer Use confirms availability.
  Each exception is authorized by its task request; do not ask the user to
  confirm each daily run.
- Before running 武装降临, use Computer Use on the current page to confirm the
  animation checkbox state, free-draw state, and number of currently claimable
  task rows. Pass these observations as `--skip-animation-state`,
  `--free-draw-state`, and `--task-claims`; for `daily-rewards`, use the
  `--armed-` prefixed forms. For direct CLI use, these are explicit per-run
  evidence gates; missing values skip the phase. In the App, the saved form
  defaults are `checked`, `available`, and 3, so compare them with the current
  page and edit the shared command parameter before live execution when needed.
- The task list rearranges after claims. Each confirmed claim click targets the
  current first claim row, waits for refresh, and dismisses its reward before
  the next click. Never treat the task count as a fixed row map.
- The free-draw ad button becomes a coupon-cost draw after success. Click it at
  most once, wait 33 seconds, close through the calibrated top ad close, check
  that the game returned, then dismiss the reward. Never retry the draw button.
- For 拟态牌库, pass this-run observations as
  `--mimic-skip-animation-state`, `--mimic-free-draw-state`, and
  `--mimic-task-claims`, plus `--mimic-one-click-claim-state` for the red-dot
  reward page, including with `daily-rewards`. Missing CLI values safely
  skip this phase and make the daily result `partial`; the App form defaults
  are checked/available/3 and must be compared with the current page. The task claims only the
  confirmed number of current first task rows, dismisses each reward, then
  opens the top-right reward page and uses its green free one-click button;
  never click adjacent paid choices.
- For 机械震荡, pass this-run observations as
  `--mechanical-shock-skip-animation-state`, `--mechanical-shock-task-claims`
  (0 through 3), and `--mechanical-shock-mech-fight-claim-state`. Missing CLI
  values safely skip this phase and make the daily result `partial`; the App
  form defaults are checked/available/3 and must be compared with the current
  page. Click the animation
  box only when it is currently unchecked, claim only the confirmed current
  first task rows, and use the mech-fight one-click claim only when it is
  currently available. Close the task list, open the bottom-right 机甲械斗 tab,
  then use `back_bottom_left` to return to game Home.
- On the verified patrol panel, `快速巡逻 x5` is the normal free quick-patrol
  button state, not a paid/currency cost. This exception applies only after the
  patrol panel is visible and the quick-patrol count is shown.
- Never confirm RMB, recharge, 月卡, 首充, paid 通行证, diamonds, paid礼包,
  补签, or unclear costs.
- Red dots are hints, not proof that the next action is safe.
- Never enter legion `任务大厅`, `军团捐献`, `玩法大厅`, or `军团大厅`.
- Welfare: never do补签.
- Before any action that could spend currency, open an ad other than the
  explicitly authorized 武装降临 or 拟态牌库 free draws, or claim a commercial offer,
  re-check with Computer Use. If still uncertain, skip instead of probing.

## Start And Recovery

1. Run `open -b com.tencent.flue.WeApp`.
2. For patrol-truck-only tasks, do not call Computer Use. Run helper
   `bounds --fit`; continue only when it succeeds, then run
   `patrol-full-from-home`. Do not gate this shell flow on `state`, because it
   can observe the terminal as the foreground app.
3. For non-patrol tasks, call `mcp__computer_use.get_app_state({"app":"微信"})`
   before any click and continue only when the window is `向僵尸开炮`.
4. Run helper `state`; continue fixed clicking only when it returns
   `game_ready`. If it returns `wechat_not_game`, `wrong_app`, or
   `bad_geometry`, do not screenshot repeatedly; use one recovery gate or stop
   according to the visible blocker.
5. Run helper `bounds`; stop fixed clicking if it aborts.
   Prefer `bounds --fit` at the start of a daily run so fixed clicks use the
   calibrated `508x949` coordinate space and do not need per-action screenshots.
6. If Computer Use reports `The user changed '微信'`, blank WeChat,
   `windowNotFoundAtPosition`, login prompts, or an unexpected page, stop
   batching. Re-query Computer Use, retry `open -b` once if needed, and resume
   only after the game is visible and helper `bounds` passes.
7. If WeChat shows `为了你的账号安全，请重新登录`, `进入微信`, or `扫码登录`, stop after
   one safe dismiss/enter attempt. Do not scan QR codes, do not ask for
   credentials, and do not continue reward navigation from the login screen.
8. If the safe dismiss leaves a blank `微信` window instead of the game, stop the
   daily run immediately. Do not re-open the mini game and continue claiming
   rewards in the same run; report the login blocker.

## Click Tiers

- Tier 0: deterministic harmless actions. Use helper clicks directly for
  `patrol_truck`, `patrol_claim`, `quick_patrol`, `quick_patrol_icon`,
  `patrol_close`, `reward_dismiss`, `ad_close_top`, `ad_close_lower`,
  `back_top_left`, and
  `back_bottom_left`, `close_top_right`, `legion_modal_close`,
  `battle_tab`, `calendar_top`, `shop_tab`, and `legion_tab`.
- Tier 1: batched routines after one script state gate or Computer Use gate.
  For full patrol-truck tasks, use `patrol-full-from-home` directly from the
  home page without screenshots. Use legacy patrol income, normal quick patrol,
  or patrol-ad subcommands only for partial reruns. Also use Tier 1 for calendar
  gift, battle-pass free claim,
  work-plan sign-in, the single free legion daily cut, and the visible legion
  all-rewards claim with `legion-reward-claims`. Read the visible
  count/state once, perform the known click/dismiss sequence, then verify at the
  next meaningful count, reward popup, or completion point. For patrol ads,
  default to the helper's `patrol-ads-batch` command after confirming the panel
  shows `观看广告`; do not screenshot inside the batch.
- Tier 2: paid, commercial, currency, non-patrol ads other than the explicitly
  authorized 武装降临 and 拟态牌库 free draws, or ambiguous surfaces.
  Re-capture immediately before the action. Click only when the visible button
  is direct-free and safe; otherwise skip.

## Patrol

Default patrol-truck task from the home page:

```bash
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py patrol-full-from-home
```

This command performs the whole patrol routine without screenshots: it checks
the calibrated game-window bounds, fits the window to the calibrated
`508x949` geometry, opens the patrol truck, attempts patrol income, runs normal
quick patrol 3 times, runs patrol ad rewards 5 times, dismisses each reward
popup with one safe tap, and closes the patrol panel.

Use `--quick-times N` or `--ad-times N` only when the user explicitly asks for a
non-default count. Use `--dry-run` with `--mock-bounds 2,33,508,949` to inspect
the planned points and waits without clicking; mock patrol dry-runs never focus
or locate a game window. During an ad cycle, if the top close does not return to
the calibrated game window after the configured reward wait, the helper stops
without tapping `ad_close_lower`. Do not add Computer Use screenshots before,
during, or after this patrol-only command. If it fails closed because the window
is not `向僵尸开炮` or the geometry is invalid, stop and report the blocker instead
of probing with screenshots.

Legacy patrol subcommands remain available for recovery or partial reruns:
`click patrol_truck`, `click patrol_claim`, `patrol-quick-batch`,
`patrol-ads-batch`, and `patrol-ads-from-home`. Use them only when the user
requests a partial patrol action or the full command is not appropriate. Never
click the quick-patrol `+`.

## Armed Descent

Use this route only with the three current-run Computer Use gates described in
Safety. Example standalone command:

```bash
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py armed-descent --skip-animation-state checked --free-draw-state available --task-claims 2
```

The command follows the calibrated route: enter 武装降临 from Home; click the
skip-animation checkbox only when the observed state is unchecked; claim the
available free ad once, wait 33 seconds, close the ad, verify return to the
game, and dismiss its reward; open tasks and repeat the current first claim row
only for the confirmed count, waiting for refresh and dismissing each reward;
close the task modal; open 武库 and use its one-click free claim; dismiss that
reward; return Home with the bottom-left back action. After success the free
draw button changes to a coupon-cost draw. `claimed` suppresses the ad click;
never retry the draw button.

The shared ad and reward primitives live in `scripts/zombie_common.py`:
`run_ad_reward_cycle` handles the one-shot ad, return check, and reward
dismissal; `run_reward_claim_cycle` handles one claim, refresh wait, and one
dismissal. Patrol routes use these same primitives with patrol-specific waits.

## Mimic Card Library

For direct CLI use, pass four current-run Computer Use observations; do not
reuse values observed in an earlier run:

```bash
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py mimic-card-library --mimic-skip-animation-state unchecked --mimic-free-draw-state available --mimic-task-claims 2 --mimic-one-click-claim-state available
```

The task enters 拟态牌库 from Home; clicks the animation checkbox only if the
current observation says unchecked; optionally runs the once-daily free ad
draw; and opens the task panel. It claims only the confirmed count from the
current first row, waiting for refresh and dismissing each reward before the
next claim. It then closes the task panel, opens the top-right red-dot reward
page, clicks the green free one-click claim only when its current-run state is
`available`, and returns with two bottom-left back actions. The free draw uses
`run_ad_reward_cycle`; task-row and red-dot
rewards use `run_reward_claim_cycle`. If a click fails while the visible page
is known, the daily runner uses that page's calibrated return path; an error
during an ad or claim popup stops later phases when the page is uncertain.

## Mechanical Shock

Use this route with all three current-run page observations:

```bash
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py mechanical-shock --mechanical-shock-skip-animation-state unchecked --mechanical-shock-task-claims 2 --mechanical-shock-mech-fight-claim-state claimed
```

The example values must match the current page; they are not remembered defaults.
The task enters 机械震荡 from Home, clicks the skip-animation box only when the
current observation says unchecked, and opens the task list. It claims only the
confirmed count (0 through 3) from the current first row, using one shared
reward cycle per row, then closes the task modal. It opens the bottom-right
机甲械斗 tab and uses the one-click claim only when the current observation is
`available`; `claimed` skips that click. Finally, it uses `back_bottom_left` to
return to game Home. Daily mode accepts the same three gate flags and marks the
run partial when the phase has to be skipped.

## Battle Pass

For direct CLI use, pass two current-run observations to the standalone
command, or use their `--pass-` prefixed forms with `daily-rewards`:

```bash
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py battle-pass-daily --free-claim-state available --work-plan-sign-state available
```

The task enters 通行证 from Home and clicks only the green free `一键领取` when
`--free-claim-state available` is confirmed. It then enters 作战计划 and picks
the sign-in row for the local weekday: Monday through Friday use the five
row-specific actions, Saturday uses the existing `work_plan_sign` action, and
Sunday first makes one downward-page scroll before using that same bottom-row
action. `--work-plan-sign-state available` is required before it clicks; a
missing gate skips only that click and marks the task partial, while `claimed`
never clicks. Each successful claim uses the shared
`run_reward_claim_cycle` before returning Home.

The weekday rows use the current 508x949 page layout at x≈387 and y≈335, 435,
535, 635, and 735 for Monday through Friday; Saturday reuses the existing
`(387,844)` action. The Sunday scroll follows the left edge from `(63,840)` to
`(63,740)` once, then targets `(387,844)`. These Sunday drag points are visual
layout estimates from the current page, not live-validated helper behavior.
Never click the ¥30/¥98 offers, ¥12 options, purple make-up sign-ins, or any
other paid or ambiguous control.

## Combined Daily Rewards

Use `daily-rewards` for the full ordered daily routine:

```bash
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py daily-rewards
```

It performs the complete patrol route, gated 机械震荡, 通行证, the gated 武装降临 and 拟态牌库
routes, calendar free-gift claim, welfare free reward dismissal, mail claim,
legion daily-rewards route, then the Journey gold/wood resource claim. The command
validates and calibrates the game window once before the first action, then
preserves those bounds for all twelve phases. Missing pass gates skip only the
corresponding claim; missing mechanical-shock, armed, or mimic gates skip that phase. The run
continues later phases and reports `partial` when a required gate is missing.
These missing-gate rules describe direct CLI calls. The Desktop App sends its
saved shared command parameters to the matching daily phases; its form defaults
are documented above and should be checked against the current page before a
live run.

To resume a new run after a prior phase was recovered or stopped, pass
`--from-step N`: the legacy mapping remains `1=patrol`, `2=calendar`,
`3=welfare`, `4=mail`, `5=legion`, `6=journey`, `7=base training hall`, and
`8=shop training hall`. 机械震荡, 通行证, 武装降临 and 拟态牌库 follow patrol
only in the full run, in that order. It marks earlier phases as `skipped`, then performs the usual
focus and calibration before the selected phase. It never infers prior progress
or resumes a phase-internal click; choose a phase only after returning to its
known safe boundary.

For a business-task boundary, use `--from-task ID`. The daily command accepts:

| IDs | Put the game on this task's entry page first |
| --- | --- |
| `patrol.claim` | Home; this task opens the patrol panel |
| `patrol.quick_patrol`, `patrol.ad_patrol` | Patrol panel |
| `mechanical.shock` | Home; confirm the animation checkbox, claimable task count (0 through 3), and mech-fight one-click state, then pass all three `--mechanical-shock-*` gates |
| `pass.daily` | Home; confirm the green one-click claim and today's direct-free sign-in state on the current pages |
| `armed.descent` | Home; confirm the animation checkbox, free-draw state, and claimable task count with Computer Use, then pass all three `--armed-*` gates |
| `mimic.card_library` | Home; confirm the animation checkbox, free-draw state, claimable task count, and red-dot one-click state with Computer Use, then pass all four `--mimic-*` gates |
| `calendar`, `welfare`, `mail` | Home |
| `legion.daily_cut`, `legion.foreign_rewards` | Home; these tasks open the Legion page |
| `legion.shop_purchases`, `legion.journey_gifts` | Legion page |
| `journey.resources`, `journey.purifier` | Home |
| `base.cafeteria` | Base page |
| `base.global_rescue`, `base.global_expedition`, `base.deep_abyss`, `base.terminal_crisis`, `base.play_shop` | Training-hall list; `base.play_shop` opens the shop as part of its task |
| `base.battlefield_contest`, `base.element_trial` | Training-hall list; the command scrolls to the bottom before the task unless `--skip-scroll` is set, in which case the list must already be at the bottom |
| `shop.resource_gold` | Home |
| `shop.special_pack_gold` | Special-pack shop page |

For example, `daily-rewards --from-task legion.shop_purchases` starts at the
Legion shop task, then continues with Legion journey gifts and every later
daily phase. The summary reports skipped IDs and the remaining task suffix.
`--from-step` and `--from-task` are mutually exclusive. CLI help lists the
entry page for every accepted ID. A resume plan, including `--dry-run`, prints
the selected ID's required entry page without clicking or dragging.

To resume specifically at 机械震荡, 武装降临, or 拟态牌库, start from Home
and pass that task's current Computer Use observations. 机械震荡 needs three
gates, 武装降临 needs three, and 拟态牌库 needs four. For example:

```bash
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py daily-rewards --from-task armed.descent --armed-skip-animation-state checked --armed-free-draw-state claimed --armed-task-claims 0
```

For 机械震荡, pass the three current observations:

```bash
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py daily-rewards --from-task mechanical.shock --mechanical-shock-skip-animation-state checked --mechanical-shock-task-claims 0 --mechanical-shock-mech-fight-claim-state claimed
```

Use the standalone `armed-descent` command with the same gate values but
without the `--armed-` prefixes. `mimic-card-library` requires its four
`--mimic-*` gates both alone and in `daily-rewards`. An absent gate makes its
phase skip safely; never supply a remembered or assumed state. The legacy
`--from-step` numbering still maps 2 to calendar even though 拟态牌库 now runs
between 武装降临 and calendar.

To resume at 通行证, start from Home and use the current page observations:

```bash
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py daily-rewards --from-task pass.daily --pass-free-claim-state claimed --pass-work-plan-sign-state available
```

The standalone `battle-pass-daily` CLI command uses the same observations
without the `--pass-` prefixes. If either CLI state is unknown, leave that gate
empty so its click is skipped. The App uses its saved shared `available` form
default, which is configuration and not evidence about the current screen.

The independently runnable composite commands also accept local IDs:

| Command | IDs and required entry pages |
| --- | --- |
| `patrol-full-from-home` | `claim`=home; `quick_patrol`, `ad_patrol`=patrol panel |
| `legion-daily-rewards` | `daily_cut`, `foreign_rewards`=home; `shop`, `journey_gifts`=Legion page |
| `journey-daily-rewards` | `resources`, `purifier`=home |
| `base-training-hall` | `cafeteria`=Base page; `global_rescue`, `global_expedition`, `deep_abyss`, `terminal_crisis`, `play_shop`=training-hall list; `battlefield_contest`, `element_trial`=training-hall list (auto-scrolls to bottom unless `--skip-scroll`, which requires the list at bottom) |
| `shop-training-hall` | `resource_gold`=home; `special_pack_gold`=special-pack shop page |
| `legion-reward-claims` | `sweeps`=home; `legion_rewards`=foreign-challenge page; `personal_rewards`=Legion rewards panel |
| `legion-shop-purchases` | `gun_blueprint`, `base_powder`, `enhancer`=Legion shop list scrolled to the selected item |
| `legion-journey-gifts` | `gift_claim`=Legion page; `expedition`=Journey gift page |
| `base-training-hall-shop` | `base_powder`=play shop enhancer item; `gun_blueprint`=battle tab at the item; `base_materials`=element tab at the item |

For example, use `legion-daily-rewards --from-task shop` or
`base-training-hall --from-task element_trial`. A selected repeated batch starts
at its first iteration and uses its configured count; it does not resume inside
the batch. Earlier tasks are skipped without checking whether they succeeded.
The play-shop `skill_manual` purchase runs after `base_materials` and shares
that suffix, so it has no independent resume ID.

One failed click delivery is retried once after re-focusing the calibrated game
window. If delivery still fails after a known phase entry, the helper uses only
that phase's verified close/back path, records `recovered_failure`, and
continues with later phases. It exits 0 with a truthful `daily rewards partial`
summary in that case; partial means later free surfaces were attempted, not
visual proof of every reward claim. Game-window, login, geometry, failed
cleanup, and an ad that does not return to the calibrated game remain fatal and
stop the command without speculative clicks.

Use `--dry-run` with `--mock-bounds 2,33,508,949` to inspect all twelve flows
without focusing a game window, clicking, or sleeping. It retains the existing
defaults: three normal patrols, five patrol-ad attempts, and two legion sweeps.

## Free Red-Dot Surfaces

- `日历`: use `calendar-claim` to open once, click visible safe gift with
  `calendar_gift`, dismiss the reward, and return with `calendar_close`. Use `calendar_top` to enter
  from the home page when the top calendar icon is visible. If a weekly/activity
  calendar close misses once, use a single Computer Use close click as recovery
  and treat the helper coordinate as needing recalibration before more fixed
  clicks on that surface. If closing the calendar opens the `月卡` paid panel,
  treat it as an unexpected commercial transition: click only `close_top_right`,
  count no calendar result unless a reward popup was already visible, and do not
  retry `calendar_close` in that session.
- `邮件`: default low-token path is
  `python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py mail-claim`.
  It first opens the top-right menu with `right_menu`, then clicks the mail
  entry, clicks one-key claim, dismisses a possible reward popup, and closes by
  script. Use `mail_reward_popup_dismiss`, not generic `reward_dismiss`, because
  the mail reward popup closes from a higher center area. When the user asks for
  no screenshots, count this as attempted, not visually verified. If the helper
  misses once, stop and update the coordinate; do not screenshot-probe the mail
  page.
- `通行证`: click only free green `一键领取`. Skip paid `¥30` / `¥98`. For
  `作战计划`, claim visible `签到` only when direct-free; stop if already checked.
  Fixed clicks available after a page gate: `pass_entry`, `pass_free_claim`,
  `work_plan_tab`, and `work_plan_sign`.
- `福利`: `welfare-claim` first drags the right-side menu upward using the
  calibrated `welfare_menu_drag_start` -> `welfare_menu_drag_end` path, then
  clicks the revealed `welfare_entry` to open only the known `七日突围` welfare cluster,
  dismisses its automatic free-reward popup with
  `welfare_reward_popup_dismiss`, and returns with `back_bottom_left`. It
  never clicks within the page. Skip补签, ads, RMB,
  diamonds, `每日特惠`, paid `免费宝箱`, task pages with only `前往`, the
  `每日充值` and `累计充值` tabs, and any ambiguous commercial red dot.

## Legion

**Ordering invariant for future changes:** `legion-journey-gifts` must remain
the final task inside the legion module. It returns from the Journey map to
the legion tab as its final action, so later legion work would change the
module's final page. Keep it after every other legion action, including shop
work, and update this sequence if the route changes.

For the complete verified free-reward route, first use Computer Use to confirm
the daily-cut button is direct-free and the foreign challenge has two free
sweeps available, then run:

```bash
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py legion-daily-rewards
```

It enters the legion tab, attempts `每日一刀` once, closes its modal, then runs
the complete foreign-challenge reward route. It must not be used when a daily
cut, sweep, or reward button is paid, ad-gated, already completed, or otherwise
unclear.

Low-token default: run `每日一刀` as a default legion daily task, but do not spend
extra screenshots proving its result. The default legion run is: `每日一刀`
attempt -> `异域挑战` sweep -> visible reward rows.

1. `每日一刀`: always enter with `legion_daily_cut` during the default legion
   run. Capture once on the modal. If the modal clearly shows a direct-free
   `砍一刀`, click `legion_cut_once` once, then close or move on without verifying
   the reward result. If the modal shows a diamond cost, price, ad/video,
   unclear wording, or already-completed state, do not click the action button;
   close it with `legion_modal_close` and report that the daily-cut check was
   executed but no free cut was claimed. This satisfies the daily task without
   spending tokens to prove the outcome.
2. `异域挑战`: after one screenshot confirms the page shows `今日挑战次数: 2/2`
   and a green free `扫荡` button, run `legion-reward-claims`. It enters the
   foreign challenge, performs two sweep/confirm/dismiss cycles, opens `奖励`,
   clicks the first `军团奖励` entry once and dismisses its reward popup, switches
   to `个人奖励`, clicks its first entry once and dismisses its popup, closes the
   panel, and returns to the legion page. Each first-row click collects all
   available rewards for that tab; do not click later rows.
   The sweep dismiss uses `legion_reward_popup_dismiss`, not generic
   `reward_dismiss`. Stop if the boss is not open, the confirm prompt is not the
   free historical-damage prompt, or the count does not change.
4. Do not click legion ads/videos, strengthening costs, task pages, donation,
   hall, unverified shop offers, or unclear actions.
5. Token budget guard: if any legion helper coordinate misses once, do one
   Computer Use recovery click, update the helper, and stop that legion
   sub-flow. Do not spend repeated screenshots trying alternative points in the
   same daily run.

### Legion Expedition Gifts Subtask

`legion-journey-gifts` is appended after the legion shop subtask. It opens the
legion hub's 征途 entry (not the bottom Journey tab), waits 0.5 seconds, opens
军团礼物, waits 0.5 seconds, claims the first gift and dismisses the reward.
The 前往 click is temporarily commented out. The route then opens 扫荡,
performs exactly three sweep/dismiss cycles, closes the search dialog, clicks the red-boxed 基地
building entry on the Journey map (not the bottom 基地 tab), then clicks the
bottom legion tab to finish on the legion page. Wait 1 second after clicking
the map base entry. Normal randomized click pacing remains in addition to
these business waits. Run only after confirming
direct gift claims and enough energy for three sweeps.

The sweep costs 40 Journey energy per attempt (120 for three), with no diamond
purchase or ad. This user-authorized energy use is allowed for this subtask;
verify at least 120 energy before running. Never buy energy or confirm a
currency offer when energy is insufficient. Button coordinates were calibrated
on 2026-10-01; the map base entry was calibrated on 2026-10-02.

### Legion Shop Purchase Subtask

Use `legion-shop-purchases` when starting from the legion hub. It opens the
legion shop and reuses the canvas-list drag implementation from the base
training-hall flow, performing one segmented CoreGraphics drag with the
calibrated `legion_shop_drag_start` and `legion_shop_drag_end` points. The
command then purchases the visible gun blueprint, base powder, and enhancer at
maximum quantity, dismissing each reward and purchase modal before closing the
shop. Only run it after verifying the three direct-cost purchase rows are
visible and safe.

### Training Hall Play-Shop Purchase Subtask

Use `base-training-hall-shop` when already on the training hall page. It opens
玩法商店 and purchases 基地熔粉, 枪械图纸, 基建耗材, then the 随机技能手册
from the 军团玩法 tab, each at maximum quantity. It dismisses each reward popup
and closes each purchase modal, then closes the play shop. The route uses the
battlefield bottom drag and horizontal tab-strip drag before entering the
requested tabs. Only run it after verifying all four visible purchase actions
are direct-cost and safe.

### Global Expedition Subtask

`base-training-hall` runs this after Global Rescue. It opens the 寰球远征 card,
claims the left-side 免费 reward, dismisses the popup, then exits the event page
and selects 基地 → 历练大厅 to return to the training-hall list. Run
`base-training-hall-global-expedition` independently from that list page.

### Deep Abyss Subtask

`base-training-hall` runs the Deep Abyss route after the Global Expedition
reward is dismissed. It enters 深渊挑战, waits 0.5 seconds, starts the
challenge, waits 3 seconds, dismisses the startup
information prompts, pauses and exits to the failure result, returns and waits
2 seconds, then performs two sweep/reward-dismiss cycles. The Deep Abyss page's
back button returns to the main game, so the route selects 基地 again before
continuing the training-hall sequence.

This route attempts one challenge and two sweeps, which consume three Deep
Abyss challenge attempts. It does not inspect or replenish the count and never
clicks the adjacent `+` button.

Run `base-training-hall-deep-abyss` independently when already on the training-
hall list page. It executes the same Deep Abyss sequence and returns to the
training hall when finished.

### Training Hall Standalone Tasks

Use these commands when already on the open training-hall list page:

- `base-training-hall-global-rescue` claims the Global Rescue free reward.
- `base-training-hall-global-expedition` enters Global Expedition, claims its
  left-side free reward, dismisses the popup, and returns to the training hall.
- `base-training-hall-terminal-crisis` runs the existing free sweep.
- `base-training-hall-battlefield-contest` runs the existing sweep route five
  times by default; pass `--battle-times N` to change the count.
- `base-training-hall-element-trial` claims the visible idle reward and runs
  one existing ten-time Core Trial sweep.

Each command returns to the training-hall list. They reuse the existing
composite-route actions and waits. Terminal Crisis scrolls the list to the
bottom; Battlefield Contest and Element Trial do the same before entering
their routes. They do not replenish attempts or add purchase, ad, or ambiguous
actions. Use `--dry-run` to print planned points without clicking.

## Journey

The combined `daily-rewards` command runs this as step 6. The route remains
conservative because journey clicks can be unreliable: collect only the visible
gold and wood bubbles, dismiss each resulting reward popup, and stop on any
unexpected state.

- Count a resource collection only if a centered `恭喜` reward popup appears.
- After a fresh capture, target one visible resource bubble and stop after the
  first confirmed popup.
- For `净化者`, click `净化者` -> `招募`, then re-capture after map movement.
  Count only explicit recruit/free reward results.

### Purifier Recruit

`journey-purifier-recruit` is the free-only purifier subtask. It enters
Journey, opens 净化者, and clicks the confirmed-free 招募 button once to recruit
all available evolvers. It does not drag the window or click individual
evolver buttons. The combined `daily-rewards` Journey phase runs the existing
gold/wood collection first and then this subtask. Stop instead of running it if
招募 is no longer explicitly free.

## Shop

- `shop-training-hall` enters the shop, explicitly opens `资源`, then performs
  two long upward drags to reach the resource page bottom,
  claims only the direct-free `金币 x600`, dismisses its reward popup, then
  opens `特惠礼包` and claims/dismisses the direct-free gold card. It never
  clicks video, diamond, RMB, discount, or unclear offers.
- Enter `商城` -> `资源`; inspect visible direct-free items only.
- Click `资源` `免费` only if it is direct free. Skip video/ad icons. If an ad
  opens accidentally, close it immediately and do not wait.
- In `特惠礼包`, use `shop_special_pack_tab` only for inspection, then claim
  direct no-ad `金币 免费` with `shop_gold_free` if visible. Skip video `体力 免费`, diamonds, RMB,
  discounts, numeric prices, and unclear items.
- `shop_tab` is calibrated to the center of the bottom-left 商城 icon. If it
  leaves the user on the home page, do one Computer Use navigation click for
  that session, then update the helper rather than retrying the bad point.
- `shop_special_pack_tab` is a low-risk navigation target, but if it does not
  switch away from `资源`, do one Computer Use navigation click and update the
  helper coordinate. Do not spend extra screenshots probing shop tabs.

## Completion Report

Report material outcomes only: patrol income, normal quick-patrol count,
patrol-ad count, free red-dot surfaces claimed, legion actions, journey result
or skip reason, shop direct-free claims, commercial/ambiguous skips, blockers,
and total token usage from `functions.get_goal` / `update_goal` when available.
