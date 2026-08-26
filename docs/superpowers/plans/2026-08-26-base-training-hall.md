# 基地历练大厅任务 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add and run a safe fixed-click routine for the base training hall's Battlefield Contest and Element Trial tasks.

**Architecture:** Extend the existing action registry and parser with one command. Keep page-specific click points in the same calibrated coordinate space, and expose the full sequence through a small command function so tests can assert the route without interacting with macOS.

**Tech Stack:** Python 3, argparse, unittest, existing CoreGraphics click helper.

**Spec:** `docs/superpowers/specs/2026-08-26-base-training-hall-design.md`

## Global Constraints

- Only direct-free rewards and sweeps are allowed.
- Keep 80ms click hold and 0.5–1.0s helper pacing.
- Default battlefield sweep count is 5.
- Dry-run must not focus, click, scroll, or sleep.

### Task 1: Add the tested command route

**Files:**
- Modify: `scripts/test_zombie_click.py`
- Modify: `scripts/zombie_click.py`

- [ ] **Step 1: Write the failing tests** for parser registration/default count, exact action order, and dry-run behavior using the existing click patching helpers.
- [ ] **Step 2: Run the focused tests** with `python3 -m unittest scripts/test_zombie_click.py -v` and confirm they fail because the new command/actions do not exist.
- [ ] **Step 3: Add calibrated action names, the scroll operation abstraction, `command_base_training_hall`, and parser flags; implement only the route described in the spec.
- [ ] **Step 4: Run the focused tests again** and confirm they pass.
- [ ] **Step 5: Run `python3 scripts/zombie_click.py --mock-bounds 2,33,508,949 base-training-hall --dry-run` and inspect the printed route.
- [ ] **Step 6: Commit the implementation with `git add scripts/zombie_click.py scripts/test_zombie_click.py && git commit -m "feat: add base training hall routine"`.

### Task 2: Verify and execute the live routine

**Files:**
- Verify: `scripts/zombie_click.py`

- [ ] **Step 1:** Run `python3 -m unittest scripts/test_zombie_click.py`.
- [ ] **Step 2:** Run `python3 -m py_compile scripts/zombie_click.py` and `git diff --check`.
- [ ] **Step 3:** Open WeChat, confirm the foreground window is `向僵尸开炮`, and calibrate bounds with the existing helper.
- [ ] **Step 4:** Use Computer Use to identify/confirm the base tab, training hall, bottom scroll position, and free buttons before dispatching fixed clicks.
- [ ] **Step 5:** Run the live command and stop immediately on login, wrong window, paid wording, missing target, or unexpected popup; verify the final visible page is基地.
