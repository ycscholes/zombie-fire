# Journey Purifier Recruit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a free-only Journey purifier recruit command that claims all six visible recruiter rewards and include it in the Journey daily phase.

**Architecture:** Actions live in the registry; `journey.py` owns standalone and daily-composed flows; the CLI is the compatibility bridge. The common input layer retains safety, logging, pacing, and retries.

**Tech Stack:** Python 3, `argparse`, `unittest`, existing macOS CoreGraphics helper.

---

### Task 1: Define behavior with failing tests

**Files:** Modify `scripts/test_zombie_click.py`

- [ ] Add a parser/flow test for `journey-purifier-recruit`. Patch `prepare_command_bounds`, `perform_action`, `perform_drag`, `perform_reward_click`, and `perform_dismiss_click`. Assert: `journey_tab`, `journey_purifier_entry`, `journey_purifier_recruit`, one drag, then `journey_purifier_claim_1` through `_6`, each immediately followed by `reward_dismiss`.
- [ ] Add a composition test that patches `command_journey_resource_claim` and `command_journey_purifier_recruit`, calls `command_journey_daily_rewards`, and asserts `['resources', 'purifier']`.
- [ ] Add a mock-bounds dry-run test proving no physical input helper is called.
- [ ] Run `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest scripts.test_zombie_click -q`.

Expected: RED because the purifier parser and commands do not exist.

### Task 2: Implement the calibrated Journey flow

**Files:** Modify `scripts/zombie_actions.py`; modify `scripts/zombie_tasks/journey.py`

- [ ] Add these actions after the existing Journey resources:

```python
"journey_purifier_entry": Action(78, 674, "Journey purifier entry"),
"journey_purifier_recruit": Action(252, 716, "free purifier recruit button"),
"journey_purifier_drag_start": Action(360, 400, "purifier map drag start"),
"journey_purifier_drag_end": Action(120, 400, "purifier map drag end"),
"journey_purifier_claim_1": Action(180, 611, "top-left free purifier reward"),
"journey_purifier_claim_2": Action(250, 611, "top-middle free purifier reward"),
"journey_purifier_claim_3": Action(320, 611, "top-right free purifier reward"),
"journey_purifier_claim_4": Action(180, 748, "bottom-left free purifier reward"),
"journey_purifier_claim_5": Action(250, 748, "bottom-middle free purifier reward"),
"journey_purifier_claim_6": Action(320, 748, "bottom-right free purifier reward"),
```

- [ ] Add all six claim names to `REWARD_ACTION_NAMES`.
- [ ] Define `PURIFIER_CLAIM_NAMES = tuple(f"journey_purifier_claim_{index}" for index in range(1, 7))`.
- [ ] Implement `command_journey_purifier_recruit(args)`: prepare and scale named points; print points and return on dry-run; call the three navigation actions, `perform_drag`, then `perform_reward_click` plus `perform_dismiss_click` for each claim.
- [ ] Implement `command_journey_daily_rewards(args)` by calling the existing resource command first and returning the purifier command result.
- [ ] Run the Task 1 tests and confirm GREEN.

### Task 3: Register the command and compose daily phase 6

**Files:** Modify `scripts/zombie_click.py`, `scripts/zombie_tasks/daily.py`, `scripts/test_zombie_click.py`

- [ ] Add CLI compatibility handler entries and wrappers for `command_journey_purifier_recruit` and `command_journey_daily_rewards`.
- [ ] Register `journey-purifier-recruit` with the same `--backend` and `--dry-run` arguments as `journey-resource-claim`.
- [ ] Import `command_journey_daily_rewards` into `daily.py` and use it in the phase-6 tuple.
- [ ] Change the existing daily shared-bounds test to patch the composed Journey handler while retaining the same expected `("journey", bounds)` phase record.
- [ ] Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest scripts.test_zombie_click -q
python3 -m py_compile scripts/zombie_click.py scripts/zombie_common.py scripts/zombie_actions.py scripts/zombie_tasks/*.py
python3 scripts/zombie_click.py --mock-bounds 2,33,508,949 journey-purifier-recruit --dry-run
python3 scripts/zombie_click.py --mock-bounds 2,33,508,949 daily-rewards --dry-run
git diff --check
```

Expected: tests and compilation pass; dry-runs print the purifier action points and make no physical input; diff check is silent.

- [ ] Commit with `git add scripts/zombie_actions.py scripts/zombie_tasks/journey.py scripts/zombie_tasks/daily.py scripts/zombie_click.py scripts/test_zombie_click.py docs/superpowers/plans/2026-09-22-journey-purifier-recruit.md && git commit -m "feat: add journey purifier recruit task"`.
