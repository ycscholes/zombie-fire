# Game Window Raise Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise and verify the specific `向僵尸开炮` window before executing a game-operating helper command.

**Architecture:** The front-window snapshot will prefer the accessibility main window (`AXMain`) of the frontmost process instead of assuming its first listed window is active. The start-focus helper will issue `AXRaise` to the title-matching game window, foreground its owning process, then fail closed unless the new front-window snapshot is the same ready game window.

**Tech Stack:** Python 3 standard library (`unittest`, `unittest.mock`); macOS System Events AppleScript accessibility API.

---

## File structure

- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py` — select a process's main window, raise the exact game window, and validate that it actually became frontmost.
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py` — test focus success and failure using mocked AppleScript and window snapshots.

### Task 1: Capture and test the target-window focus contract

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`

- [ ] **Step 1: Write failing tests for game-window focus**

```python
def game_snapshot(title: str) -> dict[str, object]:
    return {
        "app": "WeChat", "bundle": "com.tencent.xinWeChat", "title": title,
        "x": 2, "y": 33, "width": 508, "height": 949,
    }


def test_focus_raises_and_accepts_the_game_window(self) -> None:
    with (
        patch.object(zombie_click, "run_osascript", return_value="WeChat\tcom.tencent.xinWeChat\t2\t33\t508\t949") as osascript,
        patch.object(zombie_click, "front_window_snapshot", return_value=game_snapshot("向僵尸开炮")),
    ):
        self.assertEqual(zombie_click.focus_game_window_at_start().width, 508)
    self.assertIn('perform action "AXRaise"', osascript.call_args.args[0])


def test_focus_rejects_a_normal_wechat_window(self) -> None:
    with (
        patch.object(zombie_click, "run_osascript", return_value="WeChat\tcom.tencent.xinWeChat\t2\t33\t508\t949"),
        patch.object(zombie_click, "front_window_snapshot", return_value=game_snapshot("微信")),
    ):
        with self.assertRaisesRegex(zombie_click.ClickError, "did not become frontmost"):
            zombie_click.focus_game_window_at_start()
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v`

Expected: FAIL because the focus script does not issue `AXRaise` and does not verify the resulting front window.

### Task 2: Raise and verify the concrete game window

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py:135-171`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py:498-531`

- [ ] **Step 1: Prefer the front process's `AXMain` window in the snapshot script**

Replace the unconditional `set frontWindow to first window` selection with a loop that selects a window whose `AXMain` attribute is true, falling back to the first window only if no main window is exposed. This makes the snapshot describe the window macOS considers active inside the frontmost WeChat process.

- [ ] **Step 2: Raise the title-matching candidate and validate the result**

Add the accessibility raise and post-focus check inside `focus_game_window_at_start()`:

```applescript
set frontmost of candidateProc to true
perform action "AXRaise" of candidateWindow
delay 0.1
```

```python
target = parse_bounds(run_osascript(script))
snapshot = front_window_snapshot()
if not looks_like_wechat(focused) or "向僵尸开炮" not in snapshot["title"]:
    raise ClickError("game window did not become frontmost: ...")
if Bounds(...) != target:
    raise ClickError("focused game window does not match selected target: ...")
return target
```

The error messages must identify the observed title and geometry. Do not relax title or bounds matching. Do not validate minimum geometry here: `patrol-full-from-home --fit` must be able to calibrate a small, correctly focused game window.

- [ ] **Step 3: Run the isolated tests**

Run: `python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v`

Expected: PASS; the positive test sees `AXRaise`, and the normal-`微信` snapshot is rejected before any command handler runs.

- [ ] **Step 4: Commit if the skill directory becomes a Git worktree**

Run: `git -C /Users/paul/.codex/skills/zombie-fire-daily status --short`

Expected: The directory currently is not a Git worktree, so do not attempt a commit.

### Task 3: Run non-clicking regression validation

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py`
- Test: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`

- [ ] **Step 1: Validate Python syntax**

Run: `python3 -m py_compile /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py /Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`

Expected: exit code 0 with no output.

- [ ] **Step 2: Run no-window helper paths**

Run: `python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py self-test && python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py --mock-bounds 2,33,508,949 dry-run click reward_dismiss`

Expected: `self-test ok` and a scaled dry-run point; neither command focuses a live window or clicks.

- [ ] **Step 3: Validate the skill package**

Run: `python3 /Users/paul/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/paul/.codex/skills/zombie-fire-daily`

Expected: `Skill is valid!`

## Self-review

- Spec coverage: Task 1 encodes acceptance and rejection criteria. Task 2 raises the target window, selects the active accessibility window, fail-closes on title or bounds mismatch, and leaves geometry calibration to the command handler. Task 3 preserves non-operating command behavior and validates the skill.
- Placeholder scan: no incomplete implementation or validation steps remain.
- Type consistency: both the focus helper and test use `Bounds`, `ClickError`, `front_window_snapshot`, and `classify_snapshot` from the same imported script module.
