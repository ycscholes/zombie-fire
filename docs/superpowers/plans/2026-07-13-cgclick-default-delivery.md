# CoreGraphics Default Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the default patrol command select `cgclick` rather than the timing-out System Events backend.

**Architecture:** Keep existing calibrated-window guards and the persistent generated CoreGraphics helper. Change only the auto-backend resolver; explicit backend names retain their single-backend semantics. Tests mock every click path.

**Tech Stack:** Python 3 standard library (`unittest.mock`, `subprocess`); macOS CoreGraphics helper compiled with `clang`.

---

### Task 1: Lock in backend selection

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py:90-120`

- [x] **Step 1: Replace the auto-order assertion**

```python
def test_auto_backend_uses_cgclick(self) -> None:
    self.assertEqual(zombie_click.click_backend_candidates("auto"), ("cgclick",))
```

- [x] **Step 2: Add a no-System-Events fallback regression**

```python
def test_auto_does_not_try_system_events_after_cgclick_failure(self) -> None:
    bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
    with (
        patch.object(zombie_click, "ensure_unchanged_game_window"),
        patch.object(zombie_click, "wait_after_click"),
        patch.object(zombie_click, "try_click_backend", return_value=(False, "unavailable")) as attempt,
    ):
        with self.assertRaisesRegex(zombie_click.ClickError, "cgclick: unavailable"):
            zombie_click.perform_click(10, 20, "auto", bounds)
    self.assertEqual([call.args[0] for call in attempt.call_args_list], ["cgclick"])
```

- [x] **Step 3: Run the focused test suite**

```bash
python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v
```

Expected: the two new auto-backend tests fail because `auto` still resolves to `system-events`; no test emits a real click.

### Task 2: Switch resolver and documentation

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py:485-493`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/SKILL.md:43-48`

- [x] **Step 1: Replace the resolver**

```python
def click_backend_candidates(backend: str) -> tuple[str, ...]:
    """Return the single backend selected for a click invocation."""
    if backend == "auto":
        return ("cgclick",)
    return (backend,)
```

- [x] **Step 2: Replace the backend paragraph**

State that default delivery uses persistent CoreGraphics `cgclick`; `System Events` is explicit-only, uses its 8-second timeout, and cannot produce `system-events click timed out` on the default patrol path.

- [x] **Step 3: Run safe validation**

```bash
python3 -m py_compile scripts/zombie_click.py scripts/test_zombie_click.py
python3 -m unittest discover -s scripts -p 'test_zombie_click.py' -v
python3 /Users/paul/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
python3 scripts/zombie_click.py self-test
python3 scripts/zombie_click.py --mock-bounds 2,33,508,949 patrol-full-from-home --dry-run
git diff --check
```

Expected: all commands exit 0 and no command emits a real click.

### Task 3: Record completion and commit

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/docs/superpowers/plans/2026-07-13-cgclick-default-delivery.md`

- [x] **Step 1: Mark Tasks 1 and 2 complete after passing validation**

Replace each completed `- [ ]` in Tasks 1 and 2 with `- [x]`.

- [x] **Step 2: Commit the delivery change**

```bash
git add SKILL.md scripts/zombie_click.py scripts/test_zombie_click.py docs/superpowers/plans/2026-07-13-cgclick-default-delivery.md
git commit -m "fix: default patrol clicks to cgclick"
git status --short
```

Expected: the working tree is clean.

## Self-review

- Spec coverage: Task 1 proves auto selection and no hidden System Events path; Task 2 implements it; Task 3 records validation and commits.
- Placeholder scan: no deferred work or unspecified code remains.
- Type consistency: `click_backend_candidates` accepts and returns backend strings used by `perform_click`.
