# Per-click Game Focus and Single Dismiss Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every real click is preceded by focus and calibrated-window verification, while changing patrol reward dismissal to one safe click.

**Architecture:** `perform_click()` remains the sole actual-click boundary: focus the calibrated game window, verify its geometry, then dispatch through one backend. Patrol code calls a single-dismiss helper that preserves the former second click as commented historical code; no action coordinates or routes change.

**Tech Stack:** Python 3 standard library, macOS Accessibility via AppleScript/CoreGraphics, `unittest`.

---

### Task 1: Lock focus and single-dismiss behavior with regression tests

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py:120-210`
- Test: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`

- [ ] **Step 1: Replace the two-dismiss expectation with one expected click**

```python
def test_reward_dismiss_clicks_once_without_an_extra_wait(self) -> None:
    bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
    points = {"reward_dismiss": (252, 853)}
    with (
        patch.object(zombie_click, "perform_click", return_value="cgclick") as click,
        patch.object(zombie_click.time, "sleep") as sleep,
    ):
        zombie_click.dismiss_reward_once(points, "cgclick", bounds, label="test reward")

    click.assert_called_once_with(252, 853, "cgclick", bounds)
    sleep.assert_not_called()
```

- [ ] **Step 2: Run the new test and verify it fails because the single-dismiss helper does not yet exist**

Run: `python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v`

Expected: the new test errors with `AttributeError` for `dismiss_reward_once`; existing tests may still pass.

- [ ] **Step 3: Add a retry-order test for the click boundary**

```python
def test_retry_refocuses_and_revalidates_before_its_second_dispatch(self) -> None:
    bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
    events: list[str] = []
    with (
        patch.object(zombie_click, "focus_game_window", side_effect=lambda _: events.append("focus")),
        patch.object(zombie_click, "ensure_unchanged_game_window", side_effect=lambda _: events.append("verify")),
        patch.object(zombie_click, "try_click_backend", side_effect=[(False, "unavailable"), (True, "")]),
        patch.object(zombie_click, "wait_after_click"),
    ):
        zombie_click.perform_click(10, 20, "cgclick", bounds)

    self.assertEqual(events, ["focus", "verify", "focus", "verify"])
```

- [ ] **Step 4: Run the focus-order test and verify it already passes as the existing click boundary is correct**

Run: `python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v`

Expected: retry-order test passes; single-dismiss test remains red until Task 2.

### Task 2: Implement one dismiss and clarify the real-click boundary

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py:548-570`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py:872-986`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py:120-210`

- [ ] **Step 1: Add concise Chinese comments at the real-click boundary**

```python
for _attempt in range(2):
    # 每次投递前重新聚焦游戏；弹窗或广告可能在两次操作之间抢走焦点。
    focus_game_window(expected_bounds)
    # 聚焦后仍须确认校准窗口未移动或缩放，避免固定坐标误点。
    ensure_unchanged_game_window(expected_bounds)
```

- [ ] **Step 2: Replace `dismiss_reward_twice` with the minimal one-click helper and retain the old second click as comments**

```python
def dismiss_reward_once(
    points: Dict[str, Tuple[int, int]],
    backend_name: str,
    bounds: Bounds,
    *,
    label: str,
) -> str:
    # 奖励弹窗关闭后不再补点同一坐标，避免第二击落到已恢复的游戏页面。
    backend = perform_click(*points["reward_dismiss"], backend_name, bounds)
    print(f"{label}: clicked reward-dismiss once via {backend}", flush=True)
    # 旧的冗余第二次点击保留作校准记录；如日后弹窗行为变化，可据此恢复。
    # backend = perform_click(*points["reward_dismiss"], backend_name, bounds)
    # print(f"{label}: clicked reward-dismiss 2/2 via {backend}", flush=True)
    return backend
```

- [ ] **Step 3: Update the three patrol call sites without changing route timing or click coordinates**

```python
backend = dismiss_reward_once(points, args.backend, bounds, label="patrol full claim")
```

Apply the same substitution in normal quick patrol and patrol-ad branches. Remove the now-unused `wait=` argument; retain surrounding `sleep_between(...)` calls.

- [ ] **Step 4: Run focused regression tests and verify green**

Run: `python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v`

Expected: exit 0; the single-dismiss test reports one `perform_click`, and per-click focus/retry tests pass.

### Task 3: Validate the command surface and record the change

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`

- [ ] **Step 1: Compile the edited helper**

Run: `python3 -m py_compile /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py`

Expected: exit 0 with no output.

- [ ] **Step 2: Validate the complete simulated daily route without focusing or clicking a real game window**

Run: `python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py --mock-bounds 2,33,508,949 daily-rewards --dry-run`

Expected: exit 0 and a `daily rewards complete` summary. This validates scheduling only, not live window focus.

- [ ] **Step 3: Run the packaged-skill validator and whitespace check**

Run: `python3 /Users/paul/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/paul/.codex/skills/zombie-fire-daily && git -C /Users/paul/.codex/skills/zombie-fire-daily diff --check`

Expected: validator success and no diff-check output.

- [ ] **Step 4: Review requirement coverage and commit only task files**

Run: `git -C /Users/paul/.codex/skills/zombie-fire-daily diff -- scripts/zombie_click.py scripts/test_zombie_click.py`

Verify: comments are Chinese and purposeful; `perform_click()` performs focus then geometry validation before every dispatch; no active second dismiss remains; old second click remains commented. Stage only these two files and commit with `fix: focus before each game click`.
