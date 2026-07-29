# Daily Rewards Failure Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `daily-rewards` tolerate bounded click-delivery and page-transition failures while preserving fail-closed behavior for unknown game state.

**Architecture:** Keep `ClickError` as the common public exception and add typed subclasses for window state, click delivery, ad return, and failed recovery. Track navigation progress in a small `PhaseProgress` object attached only to composite phase arguments; a phase runner uses that progress to perform a verified page-specific cleanup, records `completed` or `recovered_failure`, and stops on typed fatal errors. Standalone commands preserve their CLI and defaults.

**Tech Stack:** Python 3 standard library (`argparse`, `dataclasses`, `time`, `unittest.mock`).

---

## File Structure

- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py` — typed errors, click retry, ad polling, phase progress/recovery, composite summary.
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py` — regression tests for every recovery boundary and summary outcome.
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/SKILL.md` — document partial result semantics and the fatal-state guard.

### Task 1: Typed click and window failures

**Files:**

- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py`

- [ ] **Step 1: Write failing retry and no-duplicate-dispatch tests**

```python
def test_perform_click_retries_one_delivery_failure_after_revalidating(self) -> None:
    bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
    with (
        patch.object(zombie_click, "focus_game_window") as focus,
        patch.object(zombie_click, "ensure_unchanged_game_window") as verify,
        patch.object(
            zombie_click,
            "try_click_backend",
            side_effect=[(False, "unavailable"), (True, "")],
        ) as dispatch,
        patch.object(zombie_click, "wait_after_click"),
    ):
        self.assertEqual(zombie_click.perform_click(10, 20, "cgclick", bounds), "cgclick")

    self.assertEqual(dispatch.call_count, 2)
    self.assertEqual(focus.call_count, 2)
    self.assertEqual(verify.call_count, 2)

def test_perform_click_does_not_repeat_a_successful_dispatch(self) -> None:
    bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
    with (
        patch.object(zombie_click, "focus_game_window"),
        patch.object(zombie_click, "ensure_unchanged_game_window"),
        patch.object(zombie_click, "try_click_backend", return_value=(True, "")) as dispatch,
        patch.object(zombie_click, "wait_after_click"),
    ):
        zombie_click.perform_click(10, 20, "cgclick", bounds)

    dispatch.assert_called_once_with("cgclick", 10, 20)
```

- [ ] **Step 2: Run the two tests and verify they fail because delivery is attempted once**

Run:

```bash
python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v
```

Expected: `test_perform_click_retries_one_delivery_failure_after_revalidating` fails with a `ClickError` after one dispatch attempt.

- [ ] **Step 3: Add typed errors and the bounded delivery retry**

```python
class WindowStateError(ClickError):
    pass


class ClickDeliveryError(ClickError):
    pass


class AdReturnError(WindowStateError):
    pass


class PhaseRecoveryError(WindowStateError):
    pass


def perform_click(
    x: int,
    y: int,
    backend: str = "auto",
    expected_bounds: Bounds | None = None,
    wait_after: bool = True,
) -> str:
    if expected_bounds is None:
        raise ClickDeliveryError("real clicks require calibrated game-window bounds")
    failures: list[str] = []
    for _attempt in range(2):
        focus_game_window(expected_bounds)
        ensure_unchanged_game_window(expected_bounds)
        for candidate in click_backend_candidates(backend):
            clicked, reason = try_click_backend(candidate, x, y)
            if clicked:
                if wait_after:
                    wait_after_click()
                return candidate
            failures.append(f"{candidate}: {reason}")
    raise ClickDeliveryError("click backend failed: " + "; ".join(failures))
```

Convert all focus, bounds, and calibrated-window exceptions in `focus_game_window()`, `ensure_unchanged_game_window()`, and the daily preflight to `WindowStateError`; leave user-input validation errors as `ClickError`.

- [ ] **Step 4: Run the focused tests and verify the existing one-backend guarantee remains**

Run:

```bash
python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v
```

Expected: retry test passes; the backend list contains only `cgclick` for `auto`; all existing tests remain green except the known composite regressions addressed by Task 3.

### Task 2: Bounded post-ad readiness polling

**Files:**

- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py`

- [ ] **Step 1: Write failing delayed-success and timeout tests**

```python
def test_post_ad_readiness_polls_until_the_calibrated_game_returns(self) -> None:
    bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
    with (
        patch.object(
            zombie_click,
            "front_window_snapshot",
            side_effect=[
                self.game_snapshot("广告"),
                self.game_snapshot("向僵尸开炮"),
            ],
        ),
        patch.object(zombie_click.time, "monotonic", side_effect=[0.0, 0.2]),
        patch.object(zombie_click.time, "sleep") as sleep,
    ):
        zombie_click.ensure_game_ready_after_ad(bounds, timeout=2.0, interval=0.2)

    sleep.assert_called_once_with(0.2)

def test_post_ad_readiness_raises_typed_error_after_deadline(self) -> None:
    bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
    with (
        patch.object(zombie_click, "front_window_snapshot", return_value=self.game_snapshot("广告")),
        patch.object(zombie_click.time, "monotonic", side_effect=[0.0, 2.1]),
        patch.object(zombie_click.time, "sleep"),
    ):
        with self.assertRaises(zombie_click.AdReturnError):
            zombie_click.ensure_game_ready_after_ad(bounds, timeout=2.0, interval=0.2)
```

- [ ] **Step 2: Run the suite and verify both new tests fail against one-shot readiness**

Run:

```bash
python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v
```

Expected: the delayed-success test raises immediately and the typed-timeout assertion fails.

- [ ] **Step 3: Implement polling without extra click targets**

```python
POST_AD_READY_TIMEOUT_SECONDS = 8.0
POST_AD_READY_POLL_SECONDS = 0.4


def ensure_game_ready_after_ad(
    expected: Bounds,
    *,
    timeout: float = POST_AD_READY_TIMEOUT_SECONDS,
    interval: float = POST_AD_READY_POLL_SECONDS,
) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            ensure_unchanged_game_window(expected)
            return
        except WindowStateError as exc:
            if time.monotonic() >= deadline:
                raise AdReturnError(
                    "patrol ad did not return to the calibrated game window; "
                    "stop without trying ad_close_lower"
                ) from exc
            time.sleep(interval)
```

Keep the patrol command's reward-dismiss sequence after this function, so no reward dismissal happens while the ad state is unresolved.

- [ ] **Step 4: Run the focused patrol and readiness tests**

Run:

```bash
python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v
```

Expected: delayed return passes, timeout raises `AdReturnError`, and the patrol test still proves no lower ad-close click or reward dismissal after an unresolved ad.

### Task 3: Progress-aware composite recovery and honest result reporting

**Files:**

- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py`

- [ ] **Step 1: Replace fail-fast-only coverage with failing result tests**

```python
def test_daily_rewards_continues_after_a_recovered_calendar_failure(self) -> None:
    args = argparse.Namespace(mock_bounds=zombie_click.Bounds("MOCK", "mock", 2, 33, 508, 949), dry_run=True, backend="cgclick")
    with (
        patch.object(zombie_click, "command_patrol_full_from_home", return_value=0),
        patch.object(zombie_click, "command_calendar_claim", side_effect=zombie_click.ClickDeliveryError("calendar delivery failed")),
        patch.object(zombie_click, "recover_phase", return_value=None) as recover,
        patch.object(zombie_click, "command_welfare_claim", return_value=0) as welfare,
        patch.object(zombie_click, "command_mail_claim", return_value=0),
        patch.object(zombie_click, "command_legion_daily_rewards", return_value=0),
    ):
        result = zombie_click.command_daily_rewards(args)

    self.assertEqual(result, 0)
    recover.assert_called_once()
    welfare.assert_called_once()

def test_daily_rewards_stops_after_window_state_failure(self) -> None:
    args = argparse.Namespace(mock_bounds=zombie_click.Bounds("MOCK", "mock", 2, 33, 508, 949), dry_run=True, backend="cgclick")
    with (
        patch.object(zombie_click, "command_patrol_full_from_home", side_effect=zombie_click.WindowStateError("wrong app")),
        patch.object(zombie_click, "command_calendar_claim") as calendar,
    ):
        with self.assertRaisesRegex(zombie_click.WindowStateError, "wrong app"):
            zombie_click.command_daily_rewards(args)

    calendar.assert_not_called()

def test_daily_rewards_reports_completed_and_skipped_phases_before_reraising_fatal_error(self) -> None:
    args = argparse.Namespace(mock_bounds=zombie_click.Bounds("MOCK", "mock", 2, 33, 508, 949), dry_run=True, backend="cgclick")
    with (
        patch.object(zombie_click, "command_patrol_full_from_home", return_value=0),
        patch.object(zombie_click, "command_calendar_claim", side_effect=zombie_click.WindowStateError("wrong app")),
        patch.object(zombie_click, "command_welfare_claim"),
        patch.object(zombie_click, "command_mail_claim"),
        patch.object(zombie_click, "command_legion_daily_rewards"),
        patch("builtins.print") as print_mock,
    ):
        with self.assertRaisesRegex(zombie_click.WindowStateError, "wrong app"):
            zombie_click.command_daily_rewards(args)

    printed = "\\n".join(str(call.args[0]) for call in print_mock.call_args_list)
    self.assertIn("patrol=completed", printed)
    self.assertIn("calendar=fatal_failure", printed)
    self.assertIn("welfare=skipped", printed)

def test_daily_rewards_runs_patrol_in_the_phase_order(self) -> None:
    args = argparse.Namespace(mock_bounds=None, fit=True, dry_run=False, backend="cgclick")
    bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
    phases: list[tuple[str, zombie_click.Bounds]] = []
    with (
        patch.object(zombie_click, "front_window_snapshot", return_value=self.game_snapshot("向僵尸开炮")),
        patch.object(zombie_click, "fit_game_window", return_value=bounds),
        patch.object(zombie_click, "command_patrol_full_from_home", side_effect=lambda phase_args: phases.append(("patrol", phase_args.mock_bounds))),
        patch.object(zombie_click, "command_calendar_claim", side_effect=lambda phase_args: phases.append(("calendar", phase_args.mock_bounds))),
        patch.object(zombie_click, "command_welfare_claim", side_effect=lambda phase_args: phases.append(("welfare", phase_args.mock_bounds))),
        patch.object(zombie_click, "command_mail_claim", side_effect=lambda phase_args: phases.append(("mail", phase_args.mock_bounds))),
        patch.object(zombie_click, "command_legion_daily_rewards", side_effect=lambda phase_args: phases.append(("legion", phase_args.mock_bounds))),
    ):
        self.assertEqual(zombie_click.command_daily_rewards(args), 0)

    self.assertEqual(
        phases,
        [("patrol", bounds), ("calendar", bounds), ("welfare", bounds), ("mail", bounds), ("legion", bounds)],
    )
```

- [ ] **Step 2: Run the tests and verify recovery symbols and partial behavior are absent**

Run:

```bash
python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v
```

Expected: tests fail because `recover_phase` and result tracking do not exist; the phase-order test also fails until the commented patrol call is restored.

- [ ] **Step 3: Add phase data, progress marks, recovery, and runner**

```python
@dataclass
class PhaseProgress:
    name: str
    state: str = "not_entered"


@dataclass(frozen=True)
class PhaseResult:
    name: str
    status: str
    error: str | None = None


def set_phase_state(args: argparse.Namespace, state: str) -> None:
    progress = getattr(args, "phase_progress", None)
    if progress is not None:
        progress.state = state


def run_daily_phase(name: str, handler: Callable[[argparse.Namespace], int], args: argparse.Namespace) -> PhaseResult:
    progress = PhaseProgress(name)
    args.phase_progress = progress
    try:
        handler(args)
        return PhaseResult(name, "completed")
    except ClickDeliveryError as exc:
        recover_phase(progress, args)
        return PhaseResult(name, "recovered_failure", str(exc))
    except (WindowStateError, AdReturnError, PhaseRecoveryError):
        raise
```

Set phase state immediately after successful navigation actions: patrol truck, calendar entry, welfare entry, mail menu and mail entry, legion tab, daily-cut modal, foreign challenge, and reward panel. Implement `recover_phase()` with only the cleanup actions permitted by the current phase state: patrol close; calendar close; welfare bottom-left back; mail close plus menu dismiss or menu dismiss alone; legion modal close, reward-panel close, and foreign-challenge back. First call `ensure_unchanged_game_window(args.mock_bounds)`; wrap any cleanup failure in `PhaseRecoveryError`.

Restore the real patrol invocation in `command_daily_rewards()`. Run the five handlers through `run_daily_phase()`, print a final `daily rewards partial` summary when any result is `recovered_failure`, and return 0. If a typed fatal error occurs, append `fatal_failure` for its phase, append `skipped` results for unstarted phases, print the complete phase summary, then re-raise so `main()` returns exit code 2.

- [ ] **Step 4: Run the composite regression tests and inspect their output**

Run:

```bash
python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v
```

Expected: a click-delivery failure after a known phase entry yields `recovered_failure` and later phases execute; a window/ad failure stops later phases; phase order includes real patrol.

### Task 4: Document and verify the public behavior

**Files:**

- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/SKILL.md`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py`

- [ ] **Step 1: Write a failing output-semantics test**

```python
def test_daily_rewards_prints_partial_when_a_phase_recovers(self) -> None:
    args = argparse.Namespace(mock_bounds=zombie_click.Bounds("MOCK", "mock", 2, 33, 508, 949), dry_run=True, backend="cgclick")
    with (
        patch.object(zombie_click, "command_patrol_full_from_home", side_effect=zombie_click.ClickDeliveryError("delivery failed")),
        patch.object(zombie_click, "recover_phase", return_value=None),
        patch.object(zombie_click, "command_calendar_claim", return_value=0),
        patch.object(zombie_click, "command_welfare_claim", return_value=0),
        patch.object(zombie_click, "command_mail_claim", return_value=0),
        patch.object(zombie_click, "command_legion_daily_rewards", return_value=0),
        patch("builtins.print") as print_mock,
    ):
        self.assertEqual(zombie_click.command_daily_rewards(args), 0)

    self.assertTrue(any("daily rewards partial" in str(call.args[0]) for call in print_mock.call_args_list))
```

- [ ] **Step 2: Run the suite and verify the partial summary test fails**

Run:

```bash
python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v
```

Expected: assertion fails because the command currently prints only the complete message.

- [ ] **Step 3: Update the skill contract and output summary**

Add to `SKILL.md` that the combined command returns a truthful `partial` result only after phase-specific cleanup, while game-window, login, geometry, and unresolved-ad failures remain fatal. State that a partial result means some free surfaces were attempted and later phases continued; it is not visual proof of every reward claim.

- [ ] **Step 4: Run the complete verification suite**

Run:

```bash
python3 -m py_compile /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py
python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py --mock-bounds 2,33,508,949 daily-rewards --dry-run
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py self-test
python3 /Users/paul/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/paul/.codex/skills/zombie-fire-daily
git -C /Users/paul/.codex/skills/zombie-fire-daily diff --check
```

Expected: compilation succeeds, all unit tests pass, mock dry-run shows patrol through legion scheduling, self-test passes, skill validation succeeds, and no whitespace errors are reported.

- [ ] **Step 5: Commit only this task's files**

```bash
git -C /Users/paul/.codex/skills/zombie-fire-daily add \
  SKILL.md \
  scripts/zombie_click.py \
  scripts/test_zombie_click.py \
  docs/superpowers/plans/2026-07-29-daily-rewards-failure-recovery.md
git -C /Users/paul/.codex/skills/zombie-fire-daily commit -m "fix: recover daily reward phase failures"
```

Before staging, inspect `git diff --` and exclude any unrelated user changes. If calendar/welfare changes are part of the approved five-phase flow, include them only after their tests are passing.
