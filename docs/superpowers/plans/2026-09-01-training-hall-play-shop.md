# 历练大厅玩法商店子任务 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fixed-click subtask that starts in the training hall, purchases the four requested maximum-quantity shop items, and closes the play shop.

**Architecture:** Keep all calibrated points in `zombie_actions.py`; implement the reusable purchase sequence and command in `scripts/zombie_tasks/base.py`, then call it from the existing base-training-hall route. Register the command in `zombie_click.py` and assert the exact route with mocked clicks.

**Tech Stack:** Python 3, argparse, unittest, existing CoreGraphics click/drag helper.

**Spec:** `docs/superpowers/specs/2026-09-01-training-hall-play-shop-design.md`

## Global Constraints

- Start from the current verified training-hall page for the standalone subtask.
- Use existing 80ms complete taps, ordinary pacing, and calibrated canvas drags.
- Perform only the four explicitly requested purchase sequences.
- Dry-run must not focus, click, drag, or sleep.

### Task 1: Add calibrated route and tests

**Files:**
- Modify: `scripts/zombie_actions.py`
- Modify: `scripts/zombie_tasks/base.py`
- Modify: `scripts/zombie_click.py`
- Modify: `scripts/test_zombie_click.py`

**Interfaces:**
- Produce `command_base_training_hall_shop(args) -> int`.
- Register CLI command `base-training-hall-shop` with `--backend` and `--dry-run`.
- Existing `command_base_training_hall(args)` calls the new command after returning to the training-hall page.

- [ ] **Step 1: Add failing route tests** for parser registration and exact mocked click/drag order, including four `max` and four purchase confirmation clicks.
- [ ] **Step 2: Run the focused test** with `python3 -m unittest scripts.test_zombie_click.BaseTrainingHallShopTests -v`; confirm it fails because the command/actions are absent.
- [ ] **Step 3: Implement actions and route** with separate coordinates for play shop entry, each item, max, buy, reward dismissal, modal close, horizontal tab drag, battlefield drag, element/legion tabs, and shop close. Reuse the existing `scroll_to_bottom` helper for drags.
- [ ] **Step 4: Register the parser and invoke the subtask** from `command_base_training_hall` while preserving the standalone current-page entry behavior.
- [ ] **Step 5: Run the focused tests** again and confirm they pass.

### Task 2: Verify the route without live purchases

**Files:**
- Verify: `scripts/zombie_click.py`
- Verify: `scripts/test_zombie_click.py`

- [ ] **Step 1:** Run `python3 scripts/zombie_click.py --mock-bounds 2,33,508,949 base-training-hall-shop --dry-run` and inspect all action names.
- [ ] **Step 2:** Run `python3 -m unittest scripts.test_zombie_click -v`.
- [ ] **Step 3:** Run `python3 -m py_compile scripts/zombie_click.py scripts/zombie_actions.py scripts/zombie_tasks/base.py` and `git diff --check`.
- [ ] **Step 4:** Do not execute the live purchase route unless the visible buttons have been re-confirmed as safe direct-cost purchases.
