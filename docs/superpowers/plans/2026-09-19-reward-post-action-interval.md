# Reward Post-Action Interval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every reward-claim click waits more than one second before the next physical input.

**Architecture:** Add a single reward-click wrapper in `zombie_common.py` that reuses the verified click path and applies the project-level minimum wait. Replace claim-producing clicks in reward flows with that wrapper; navigation, dismiss, and drag inputs retain their existing behavior.

**Tech Stack:** Python 3, unittest, CoreGraphics click helper.

---

### Task 1: Define and verify the shared reward-click contract

**Files:**
- Modify: `scripts/test_zombie_click.py`
- Modify: `scripts/zombie_common.py`

- [ ] **Step 1: Write the failing test**

```python
def test_perform_reward_click_waits_more_than_one_second(self) -> None:
    bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
    with patch.object(zombie_click, "perform_click", return_value="cgclick") as click, \
         patch.object(zombie_click.time, "sleep") as sleep:
        zombie_click.perform_reward_click(10, 20, "cgclick", bounds)
    click.assert_called_once_with(10, 20, "cgclick", bounds, False)
    self.assertGreater(sleep.call_args.args[0], 1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest scripts.test_zombie_click.FocusEligibilityTests.test_perform_reward_click_waits_more_than_one_second`

Expected: FAIL because `perform_reward_click` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
REWARD_POST_ACTION_MIN_SECONDS = 1.05

def perform_reward_click(x, y, backend, expected_bounds):
    result = perform_click(x, y, backend, expected_bounds, False)
    time.sleep(REWARD_POST_ACTION_MIN_SECONDS)
    return result
```

Add `post_reward_wait_ms=1050.0` to successful reward-click operation logs.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest scripts.test_zombie_click.FocusEligibilityTests.test_perform_reward_click_waits_more_than_one_second`

Expected: PASS.

### Task 2: Route reward claims through the shared contract

**Files:**
- Modify: `scripts/zombie_common.py`
- Modify: `scripts/zombie_tasks/patrol.py`
- Modify: `scripts/zombie_tasks/home.py`
- Modify: `scripts/zombie_tasks/legion.py`
- Modify: `scripts/zombie_tasks/journey.py`
- Modify: `scripts/zombie_tasks/shop.py`
- Modify: `scripts/zombie_tasks/base.py`
- Test: `scripts/test_zombie_click.py`

- [ ] **Step 1: Write failing flow tests**

```python
with patch.object(zombie_click, "perform_reward_click", return_value="cgclick") as reward_click:
    zombie_click.command_journey_resource_claim(args)
self.assertEqual(reward_click.call_count, 2)
```

Add equivalent assertions for patrol claims, mail/calendar claims, legion reward claims, shop free claims, and training-hall shop purchase confirmations.

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `python3 -m unittest scripts.test_zombie_click`

Expected: targeted assertions fail because flows still use `perform_click`.

- [ ] **Step 3: Replace only claim-producing actions**

Use `perform_reward_click` for actions that acquire a reward. Keep `perform_dismiss_click` for popup closing and `perform_click` for navigation, confirmations that do not award, and modal close actions.

- [ ] **Step 4: Run targeted tests to verify they pass**

Run: `python3 -m unittest scripts.test_zombie_click`

Expected: PASS.

### Task 3: Verify the integrated rule

**Files:**
- Modify: `docs/superpowers/specs/2026-09-19-reward-post-action-interval-design.md`

- [ ] **Step 1: Run static and full-suite verification**

Run: `git diff --check && python3 -m unittest scripts.test_zombie_click`

Expected: no whitespace errors and all tests pass.

- [ ] **Step 2: Record the implementation evidence**

Update the design verification section with the exact test command and outcome; do not claim live gameplay proof unless a real run is performed.

- [ ] **Step 3: Commit scoped changes**

Run: `git add scripts/zombie_common.py scripts/zombie_tasks scripts/test_zombie_click.py docs/superpowers/specs/2026-09-19-reward-post-action-interval-design.md && git commit -m "fix: enforce reward post-action interval"`
