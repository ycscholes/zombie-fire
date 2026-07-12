# Patrol Click Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make patrol click dispatch observable, make unknown ad layouts stop safely, and restore mock patrol dry-runs without a game window.

**Architecture:** Keep one fixed-coordinate helper. `auto` uses only observable
`system-events` delivery and fails closed; CoreGraphics `cgclick` remains an
explicit opt-in backend only. Add a post-ad-close game-window gate before the
reward dismiss. Extend the existing `unittest` module through mocks only; no
test emits a mouse event.

**Tech Stack:** Python 3 standard library (`argparse`, `pathlib`, `subprocess`, `unittest.mock`); macOS `osascript`, CoreGraphics helper compiled with `clang`.

---

## File structure

- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py` — backend selection/cache, mock focus classification, and patrol ad timing/guard.
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py` — isolated regressions using patched functions.
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/.gitignore` — ignore the stable generated helper cache.
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/SKILL.md` — document the safe mock dry-run and fail-closed ad behaviour.

### Task 1: Lock in the non-clicking regressions

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`

- [x] **Step 1: Add a mock patrol dry-run dispatch test**

```python
def test_main_mock_patrol_dry_run_does_not_focus(self) -> None:
    with patch.object(zombie_click, "focus_game_window_at_start") as focus:
        self.assertEqual(
            zombie_click.main([
                "--mock-bounds", "2,33,508,949",
                "patrol-full-from-home", "--dry-run",
            ]),
            0,
        )
    focus.assert_not_called()
```

- [x] **Step 2: Add backend-order and fail-closed tests**

```python
def test_auto_backend_uses_only_system_events(self) -> None:
    self.assertEqual(
        zombie_click.click_backend_candidates("auto"),
        ("system-events",),
    )

def test_auto_does_not_fall_back_after_system_events_failure(self) -> None:
    bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
    with (
        patch.object(zombie_click, "ensure_unchanged_game_window"),
        patch.object(zombie_click, "wait_after_click"),
        patch.object(
            zombie_click,
            "try_click_backend",
            return_value=(False, "access denied"),
        ) as attempt,
    ):
        with self.assertRaisesRegex(zombie_click.ClickError, "system-events: access denied"):
            zombie_click.perform_click(10, 20, "auto", bounds)
    self.assertEqual([call.args[0] for call in attempt.call_args_list], ["system-events"])
```

- [x] **Step 3: Add stable cache and ad transition tests**

```python
def test_cgclick_cache_paths_are_stable_and_ignored(self) -> None:
    self.assertEqual(zombie_click.CGCLICK_BIN_PATH.parent, zombie_click.CGCLICK_CACHE_DIR)
    self.assertEqual(zombie_click.CGCLICK_BIN_PATH.name, "zombie_cgclick")

def test_patrol_ad_waits_before_reward_dismiss(self) -> None:
    args = zombie_click.build_parser().parse_args([
        "patrol-full-from-home", "--quick-times", "0", "--ad-times", "1", "--no-fit",
        "--panel-wait", "0", "--claim-wait", "0", "--dismiss-wait", "0", "--quick-between", "0",
        "--ad-wait", "0", "--ad-close-wait", "1.25", "--ad-reward-wait", "2.5",
        "--ad-between", "0", "--close-wait", "0",
    ])
    bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
    events: list[object] = []
    with (
        patch.object(zombie_click, "get_bounds", return_value=bounds),
        patch.object(zombie_click, "front_window_snapshot", return_value=self.game_snapshot("向僵尸开炮")),
        patch.object(zombie_click, "perform_click", return_value="system-events") as click,
        patch.object(zombie_click, "sleep_between", side_effect=lambda value: events.append(("sleep", value))),
        patch.object(zombie_click, "ensure_game_ready_after_ad", side_effect=lambda _: events.append("ready")),
    ):
        self.assertEqual(zombie_click.command_patrol_full_from_home(args), 0)
    self.assertEqual(events[6:9], [("sleep", 1.25), ("sleep", 2.5), "ready"])
    self.assertEqual(click.call_count, 9)
```

- [x] **Step 4: Run the focused suite and confirm the new tests fail**

Run:

```bash
python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v
```

Result: the initial focused suite exposed the missing mock-focus exemption,
backend policy, stable-path constants, and ad-reward delay; the corresponding
regressions are now covered without dispatching a mouse event.

### Task 2: Implement explicit backend and simulation behaviour

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py:24-58`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py:394-475`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py:1204-1221`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/.gitignore`

- [x] **Step 1: Add the persistent generated-helper paths and ignore rule**

```python
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
CGCLICK_CACHE_DIR = SKILL_ROOT / ".generated"
CGCLICK_BIN_PATH = CGCLICK_CACHE_DIR / "zombie_cgclick"
CGCLICK_SOURCE_PATH = CGCLICK_CACHE_DIR / "zombie_cgclick.c"
```

Append this `.gitignore` entry:

```gitignore
.generated/
```

- [x] **Step 2: Compile only when the stable helper is absent**

```python
def ensure_cgclick() -> bool:
    global CGCLICK_BIN
    if CGCLICK_BIN and os.path.exists(CGCLICK_BIN) and os.access(CGCLICK_BIN, os.X_OK):
        return True
    if CGCLICK_BIN_PATH.exists() and os.access(CGCLICK_BIN_PATH, os.X_OK):
        CGCLICK_BIN = str(CGCLICK_BIN_PATH)
        return True
    CGCLICK_CACHE_DIR.mkdir(mode=0o700, exist_ok=True)
    CGCLICK_SOURCE_PATH.write_text(CGCLICK_SOURCE, encoding="utf-8")
    proc = subprocess.run(
        ["clang", "-framework", "ApplicationServices", str(CGCLICK_SOURCE_PATH), "-o", str(CGCLICK_BIN_PATH)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        return False
    CGCLICK_BIN = str(CGCLICK_BIN_PATH)
    return True
```

- [x] **Step 3: Make `auto` observable and fail closed**

```python
def click_backend_candidates(backend: str) -> tuple[str, ...]:
    if backend == "auto":
        # Auto must expose macOS Accessibility failures rather than silently
        # replacing them with an unverifiable CoreGraphics post.
        return ("system-events",)
    return (backend,)

def perform_click(x: int, y: int, backend: str = "auto", expected_bounds: Bounds | None = None) -> str:
    if expected_bounds is None:
        raise ClickError("real clicks require calibrated game-window bounds")
    ensure_unchanged_game_window(expected_bounds)
    failures = []
    for candidate in click_backend_candidates(backend):
        clicked, reason = try_click_backend(candidate, x, y)
        if clicked:
            wait_after_click()
            return candidate
        failures.append(f"{candidate}: {reason}")
    raise ClickError("click backend failed: " + "; ".join(failures))
```

- [x] **Step 4: Exempt mock dry-runs from focus**

```python
def command_requires_focus(args: argparse.Namespace) -> bool:
    if args.command in NON_OPERATING_COMMANDS:
        return False
    return not (bool(getattr(args, "mock_bounds", None)) and bool(getattr(args, "dry_run", False)))
```

Call it as `command_requires_focus(args)` in `main()` and update the existing
focus-eligibility tests to pass parsed-command-shaped arguments or introduce a
separate pure helper for the command-name portion.

- [x] **Step 5: Run the focused suite**

Run the Task 1 command.

Result: all existing focus tests and the new backend/mock tests pass, with no
mouse event. `cgclick` remains available only when explicitly supplied through
`--backend cgclick`.

### Task 3: Make the full patrol ad branch fail closed

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py:761-879`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`

- [x] **Step 1: Add a pure post-ad-close readiness helper**

```python
def ensure_game_ready_after_ad(expected: Bounds) -> None:
    try:
        ensure_unchanged_game_window(expected)
    except ClickError as exc:
        raise ClickError(
            "patrol ad did not return to the calibrated game window; "
            "stop without trying ad_close_lower"
        ) from exc
```

- [x] **Step 2: Use the configured reward delay and readiness gate**

Immediately after the existing `ad_close_wait` in the `patrol-full-from-home`
ad loop, add:

```python
sleep_between(args.ad_reward_wait)
ensure_game_ready_after_ad(bounds)
```

Then retain the existing `dismiss_reward_twice` call. Do not add `ad_close_lower` to
`patrol_full_points()` or the full routine.

- [x] **Step 3: Run the isolated patrol tests**

Run the Task 1 command.

Result: the tests observe `ad_close_wait`, then `ad_reward_wait`, then the
game-readiness gate; a readiness failure stops before any reward dismiss or
`ad_close_lower` click.

### Task 4: Document and validate the repaired helper

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/SKILL.md`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/docs/superpowers/plans/2026-07-12-patrol-click-reliability.md`

- [x] **Step 1: Correct the patrol preflight and backend documentation**

Replace the patrol-only `state` preflight with `bounds --fit`, explaining that
`state` observes the current foreground app and can report the terminal when
run from a shell. State that `auto` uses only `system-events`, waits up to 8
seconds for that dispatch, and fails closed rather than falling back to
`cgclick`; `cgclick` remains explicit only. Also state that mock patrol
dry-runs do not focus or locate a game window, and that an ad close which does
not return to the calibrated game window stops the run without tapping
`ad_close_lower`.

- [x] **Step 2: Mark completed plan checkboxes and run the complete safe validation**

```bash
python3 -m py_compile scripts/zombie_click.py scripts/test_zombie_click.py
python3 -m unittest discover -s scripts -p 'test_zombie_click.py' -v
python3 /Users/paul/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
python3 scripts/zombie_click.py self-test
python3 scripts/zombie_click.py --mock-bounds 2,33,508,949 patrol-full-from-home --dry-run
git diff --check
```

Result: all commands exited 0. The focused suite ran 15 tests; the skill
validator reported `Skill is valid!`; `self-test` passed; the mock patrol command
printed its plan without a game-window lookup; and `git diff --check` passed.
None of these commands emits a real click.

- [ ] **Step 3: Commit the implementation**

```bash
git add .gitignore SKILL.md scripts/zombie_click.py scripts/test_zombie_click.py \
  docs/superpowers/plans/2026-07-12-patrol-click-reliability.md
git commit -m "fix: harden patrol click delivery"
git status --short
```

Expected: the commit contains the reliability repair and the working tree is
clean.

## Self-review

- Spec coverage: Task 2 covers stable backend selection/cache and mock
  simulation; Task 3 covers ad timing and fail-closed recovery; Task 4 covers
  documentation and each required safe validation.
- Placeholder scan: no `TBD`, `TODO`, or deferred implementation work remains.
- Type consistency: `click_backend_candidates()` receives a backend string;
  `command_requires_focus()` receives the parsed namespace; all `Bounds`
  values preserve the existing immutable dataclass contract.
