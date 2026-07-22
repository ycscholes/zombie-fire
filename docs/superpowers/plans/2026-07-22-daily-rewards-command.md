# Daily Rewards Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single fail-fast `daily-rewards` command for patrol, mail, and legion reward routes.

**Architecture:** The composite command will validate and calibrate the game window once, then invoke the three existing command handlers with a copied argument namespace sharing the same mock bounds. Dry runs will call the same handlers with their existing dry-run modes, so no clicks or sleeps occur.

**Tech Stack:** Python 3 standard library, `argparse`, `unittest.mock`.

---

### Task 1: Define the composite behavior with tests

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`
- Test: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`

- [x] **Step 1: Write failing tests**

```python
def test_daily_rewards_runs_patrol_mail_then_legion_with_one_bounds_value(self) -> None:
    args = zombie_click.build_parser().parse_args(["daily-rewards"])
    bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
    with patch.object(zombie_click, "prepare_command_bounds", return_value=bounds), \
         patch.object(zombie_click, "command_patrol_full_from_home", return_value=0) as patrol, \
         patch.object(zombie_click, "command_mail_claim", return_value=0) as mail, \
         patch.object(zombie_click, "command_legion_daily_rewards", return_value=0) as legion:
        self.assertEqual(zombie_click.command_daily_rewards(args), 0)
    self.assertEqual([patrol.call_count, mail.call_count, legion.call_count], [1, 1, 1])

def test_daily_rewards_stops_after_a_failed_phase(self) -> None:
    args = zombie_click.build_parser().parse_args(["daily-rewards"])
    with patch.object(zombie_click, "command_patrol_full_from_home", side_effect=zombie_click.ClickError("stop")), \
         patch.object(zombie_click, "command_mail_claim") as mail:
        with self.assertRaisesRegex(zombie_click.ClickError, "stop"):
            zombie_click.command_daily_rewards(args)
    mail.assert_not_called()
```

- [x] **Step 2: Run the focused tests and verify they fail because `daily-rewards` is not registered**

Run: `python3 -m unittest scripts/test_zombie_click.py`

Expected: failure mentioning the unknown `daily-rewards` command.

### Task 2: Add the minimal command and parser wiring

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py`

- [x] **Step 1: Implement a shared-bounds command handler**

```python
def command_daily_rewards(args: argparse.Namespace) -> int:
    bounds = prepare_command_bounds(args)
    phase_args = argparse.Namespace(**vars(args), mock_bounds=bounds, fit=False)
    command_patrol_full_from_home(phase_args)
    command_mail_claim(phase_args)
    command_legion_daily_rewards(phase_args)
    return 0
```

The actual implementation must preserve the one-time non-mock game readiness
check and pass the existing `dry_run` and backend values to each phase.

- [x] **Step 2: Register the parser**

```python
daily_parser = sub.add_parser("daily-rewards", help="run patrol, mail, and legion daily rewards")
daily_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
daily_parser.add_argument("--dry-run", action="store_true")
daily_parser.set_defaults(func=command_daily_rewards)
```

- [x] **Step 3: Run the focused unit suite and verify it passes**

Run: `python3 -m unittest scripts/test_zombie_click.py`

Expected: exit code 0.

### Task 3: Document and simulate the public command

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/SKILL.md`

- [x] **Step 1: Add the command to the usage list and document its fail-fast, shared-window behavior**

```bash
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py daily-rewards
```

- [x] **Step 2: Verify the combined dry run does not click**

Run: `python3 scripts/zombie_click.py --mock-bounds 2,33,508,949 daily-rewards --dry-run`

Expected: exit code 0 and combined patrol, mail, and legion dry-run output.

- [x] **Step 3: Check whitespace errors**

Run: `git diff --check`

Expected: exit code 0.
