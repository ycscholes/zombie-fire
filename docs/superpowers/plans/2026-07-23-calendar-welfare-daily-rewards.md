# Calendar and Welfare Daily Rewards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe calendar and right-side welfare free-reward routes to the helper and composite daily routine.

**Architecture:** Add two narrow command functions to `zombie_click.py`, each using `prepare_command_bounds()` and named existing action coordinates. Extend the composite command to invoke those functions with the calibrated shared bounds; tests assert ordered clicks and delegation.

**Tech Stack:** Python 3 standard library, argparse, unittest.

---

### Task 1: Calendar and welfare command flows

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py`
- Test: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`

- [ ] **Step 1: Write failing ordered-flow tests**

```python
def test_calendar_claim_clicks_entry_gift_dismiss_and_close(self) -> None:
    # Assert calendar_top, calendar_gift, reward_dismiss, calendar_close.

def test_welfare_claim_clicks_only_free_popup_dismiss_and_back(self) -> None:
    # Assert welfare_cluster, reward_dismiss, back_bottom_left.
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v`

Expected: failure because `calendar-claim` and `welfare-claim` do not exist.

- [ ] **Step 3: Implement the minimal commands and CLI parsers**

```python
def command_calendar_claim(args: argparse.Namespace) -> int:
    # prepare bounds; click calendar_top, calendar_gift, reward_dismiss,
    # calendar_close; support --dry-run.

def command_welfare_claim(args: argparse.Namespace) -> int:
    # prepare bounds; click welfare_cluster, reward_dismiss, back_bottom_left;
    # support --dry-run and never enter recharge tabs.
```

- [ ] **Step 4: Run the focused tests and mock dry-runs**

Run: `python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v && python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py --mock-bounds 2,33,508,949 calendar-claim --dry-run && python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py --mock-bounds 2,33,508,949 welfare-claim --dry-run`

Expected: all focused tests pass and both dry-runs print their calibrated flow.

### Task 2: Composite daily integration and documentation

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/SKILL.md`

- [ ] **Step 1: Write a failing composite delegation test**

```python
def test_daily_rewards_runs_patrol_calendar_welfare_mail_and_legion(self) -> None:
    # Patch all five commands and assert shared mock bounds plus ordered calls.
```

- [ ] **Step 2: Extend `command_daily_rewards()`**

```python
# Preserve calibrated bounds and fail-fast execution:
command_patrol_full_from_home(...)
command_calendar_claim(...)
command_welfare_claim(...)
command_mail_claim(...)
command_legion_daily_rewards(...)
```

- [ ] **Step 3: Update the skill contract**

Document the two standalone commands, the new composite order, and the welfare
rule excluding recharge tabs and all non-free offers.

- [ ] **Step 4: Run full local verification**

Run: `python3 -m py_compile /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py && python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v && python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py --mock-bounds 2,33,508,949 daily-rewards --dry-run && python3 /Users/paul/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/paul/.codex/skills/zombie-fire-daily && git -C /Users/paul/.codex/skills/zombie-fire-daily diff --check`

Expected: all new tests and dry-run pass; report any pre-existing unrelated test failure separately.
