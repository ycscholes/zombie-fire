# Click Helper Safety Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every real fixed click fail closed when the window context changes, while preserving the low-token command interface.

**Architecture:** Keep calibration and actions unchanged. Centralize invocation validation, frontmost-game-window validation, backend error normalization, and numeric argument validation in the helper so every command gets the same safeguards.

**Tech Stack:** Python 3 standard library, macOS System Events, CoreGraphics helper compiled with clang.

---

### Task 1: Add invocation and argument safety checks

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py`

- [x] Reject real action commands supplied with `--mock-bounds`; retain mock dry-runs and read-only bounds inspection.
- [x] Replace float wait argument parsing with a finite non-negative parser for every configurable delay and sequence interval.
- [x] Verify the rejected paths without issuing a click:

```bash
python3 zombie_click.py --mock-bounds 0,0,508,949 mail-claim
python3 zombie_click.py patrol-quick-batch --times 1 --between -1 --dry-run
```

Expected: both commands return exit code 2 with a clear validation error.

### Task 2: Guard every real click against live window drift

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py`

- [x] Make `front_window_snapshot()` report the actual frontmost window rather than an arbitrary matching game window.
- [x] Add an expected-bounds guard to `perform_click()` and pass the calibrated bounds from every click flow.
- [x] Abort before a click when the frontmost game title, application identity, or full bounds tuple differs from the expected game window.
- [x] Verify with `self-test`, mock dry-runs, and a monkeypatched no-click guard test.

### Task 3: Make backend failure handling deterministic

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py`

- [x] Wrap backend subprocess and Quartz errors as `ClickError`.
- [x] Let `auto` try all configured backends after an individual backend fails; keep an explicit backend fail-closed.
- [x] Allocate the generated CoreGraphics helper in a private `tempfile.mkdtemp()` directory rather than fixed `/tmp` paths.
- [x] Run Python compilation and helper validation:

```bash
python3 -m py_compile zombie_click.py
python3 /Users/paul/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/paul/.codex/skills/zombie-fire-daily
```

Expected: both commands succeed.
