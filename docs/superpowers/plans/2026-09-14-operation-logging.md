# Operation Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit one auditable log line for every real click and drag operation.

**Architecture:** Keep operation telemetry at the shared input boundary in `zombie_common.py`. Clicks retain their existing `perform_click` API; a new `perform_drag` owns focus validation, delivery and reporting so task modules cannot omit drag logs.

**Tech Stack:** Python 3 standard library, unittest, macOS CoreGraphics helper.

---

### Task 1: Define operation-log behaviour with regression tests

**Files:**
- Modify: `scripts/test_zombie_click.py`
- Test: `scripts/test_zombie_click.py`

- [ ] **Step 1: Write failing click-log tests**

```python
def test_perform_click_logs_successful_delivery(self) -> None:
    ...
    self.assertIn("operation: click status=success backend=cgclick point=(10,20)", output.getvalue())
```

- [ ] **Step 2: Run the focused test and verify it fails because the log is absent**

Run: `python3 -m unittest scripts.test_zombie_click.FocusEligibilityTests.test_perform_click_logs_successful_delivery`

- [ ] **Step 3: Write failing drag-log tests for success and delivery failure**

```python
def test_perform_drag_logs_the_start_end_and_success(self) -> None:
    ...
    self.assertIn("operation: drag status=success backend=cgclick start=(10,20) end=(30,40)", output.getvalue())
```

- [ ] **Step 4: Run the focused drag tests and verify they fail because `perform_drag` is absent**

Run: `python3 -m unittest scripts.test_zombie_click.FocusEligibilityTests.test_perform_drag_logs_the_start_end_and_success`

### Task 2: Implement shared click and drag logging

**Files:**
- Modify: `scripts/zombie_common.py`
- Test: `scripts/test_zombie_click.py`

- [ ] **Step 1: Add the minimal `log_operation` formatter and call it after click dispatch succeeds or fails**

```python
print(f"operation: {kind} status={status} ...", flush=True)
```

- [ ] **Step 2: Add `perform_drag` to focus, validate, dispatch, log and raise `ClickDeliveryError` on unavailable delivery**

```python
def perform_drag(x1, y1, x2, y2, expected_bounds):
    focus_game_window(expected_bounds)
    ensure_unchanged_game_window(expected_bounds)
    ...
```

- [ ] **Step 3: Run the focused click and drag tests and verify they pass**

Run: `python3 -m unittest scripts.test_zombie_click.FocusEligibilityTests`

### Task 3: Route task drags through the shared boundary

**Files:**
- Modify: `scripts/zombie_click.py`
- Modify: `scripts/zombie_tasks/base.py`
- Modify: `scripts/zombie_tasks/home.py`
- Test: `scripts/test_zombie_click.py`

- [ ] **Step 1: Update compatibility forwarding to expose `perform_drag` to extracted tasks**

```python
def perform_drag(*args, **kwargs):
    return _common_call("perform_drag", *args, **kwargs)
```

- [ ] **Step 2: Replace direct task calls to `drag_cgclick_bin` with `perform_drag`**

```python
perform_drag(x1, y1, x2, y2, bounds)
```

- [ ] **Step 3: Adjust task tests to patch and assert `perform_drag`, then run focused task tests**

Run: `python3 -m unittest scripts.test_zombie_click.BaseTrainingHallTests scripts.test_zombie_click.FocusEligibilityTests`

### Task 4: Verify the complete helper

**Files:**
- Test: `scripts/test_zombie_click.py`

- [ ] **Step 1: Run all helper tests**

Run: `python3 -m unittest scripts.test_zombie_click`

- [ ] **Step 2: Run a mock dry-run to confirm planned actions remain non-operating**

Run: `python3 scripts/zombie_click.py --mock-bounds 2,33,508,949 welfare-claim --dry-run`

- [ ] **Step 3: Check the scoped diff for whitespace errors and unintended files**

Run: `git diff --check -- scripts/zombie_common.py scripts/zombie_click.py scripts/zombie_tasks/base.py scripts/zombie_tasks/home.py scripts/test_zombie_click.py`
