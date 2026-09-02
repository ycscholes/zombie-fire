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
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py base-training-hall-shop
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py shop-training-hall
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

Every helper click waits a random `0.4` to `0.6` seconds before the next helper
operation. Do not bypass this pacing when adding new scripted click flows.
Reward-popup dismiss clicks use a fixed 1-second wait after dismissal before
the next operation.

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
  patrol -> calendar -> welfare cluster -> shop inspection -> battle pass /
  work-plan sign-in -> legion. Capture once per entered surface, then use fixed
  clicks for known free claim buttons and reward dismissal. In legion, capture
  at most once on the legion hub and once on the foreign-challenge page unless a
  verified free reward is already open.
- When a surface has a page-specific bottom-left back button or inner modal
  close, use `back_bottom_left` or `legion_modal_close`; do not retry
  `back_top_left` / `close_top_right` on those surfaces.
- If a helper coordinate misses once on a verified page, use one Computer Use
  recovery click for that session, update the helper coordinate, and stop
  retrying the stale helper point.

## Safety

- Claim only free rewards.
- Watch ads only for patrol-truck `观看广告`; skip all other ad/video rewards.
- On the verified patrol panel, `快速巡逻 x5` is the normal free quick-patrol
  button state, not a paid/currency cost. This exception applies only after the
  patrol panel is visible and the quick-patrol count is shown.
- Never confirm RMB, recharge, 月卡, 首充, paid 通行证, diamonds, paid礼包,
  补签, or unclear costs.
- Red dots are hints, not proof that the next action is safe.
- Never enter legion `任务大厅`, `军团捐献`, `玩法大厅`, or `军团大厅`.
- Welfare: never do补签.
- Before any action that could spend currency, open an ad outside patrol, or
  claim a commercial offer, re-check with Computer Use. If still uncertain,
  skip instead of probing.

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
- Tier 2: paid, commercial, currency, non-patrol ad, or ambiguous surfaces.
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

## Combined Daily Rewards

Use `daily-rewards` when the requested scope is exactly patrol, mail, and
legion free rewards:

```bash
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py daily-rewards
```

It performs the complete patrol route, calendar free-gift claim, welfare free
reward dismissal, mail claim, legion daily-rewards route, then the Journey
gold/wood resource claim. The command
validates and calibrates the game window once before the first action, then
preserves those bounds for all eight phases.

To resume a new run after a prior phase was recovered or stopped, pass
`--from-step N`: `1=patrol`, `2=calendar`, `3=welfare`, `4=mail`, `5=legion`,
`6=journey`, `7=base training hall`, and `8=shop training hall`. It marks earlier phases as `skipped`, then performs the usual
focus and calibration before the selected phase. It never infers prior progress
or resumes a phase-internal click; choose a phase only after returning to its
known safe boundary.

One failed click delivery is retried once after re-focusing the calibrated game
window. If delivery still fails after a known phase entry, the helper uses only
that phase's verified close/back path, records `recovered_failure`, and
continues with later phases. It exits 0 with a truthful `daily rewards partial`
summary in that case; partial means later free surfaces were attempted, not
visual proof of every reward claim. Game-window, login, geometry, failed
cleanup, and an ad that does not return to the calibrated game remain fatal and
stop the command without speculative clicks.

Use `--dry-run` with `--mock-bounds 2,33,508,949` to inspect all eight flows
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
- `福利`: `welfare-claim` opens only the known `七日突围` welfare cluster,
  dismisses its automatic free-reward popup with
  `welfare_reward_popup_dismiss`, and returns with `back_bottom_left`. It
  never clicks within the page. Skip补签, ads, RMB,
  diamonds, `每日特惠`, paid `免费宝箱`, task pages with only `前往`, the
  `每日充值` and `累计充值` tabs, and any ambiguous commercial red dot.

## Legion

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
玩法商店, purchases 基地熔粉, 枪械图纸, 基建耗材, and 随机技能手册 at maximum
quantity, dismisses each reward popup and closes each purchase modal, then
closes the play shop. It uses the battlefield bottom drag and the horizontal
tab-strip drag before entering the requested tabs. Only run it after verifying
the four visible purchase actions are direct-cost and safe.

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
