# Legion Reward Claims Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Centralize the foreign-challenge reward claim sequence in a safe, one-click `legion-reward-claims` command and reuse it from the daily legion route.

**Architecture:** `command_legion_reward_claims()` owns foreign-challenge navigation and one first-row all-rewards claim, followed by the legion-specific popup dismiss. `command_legion_daily_rewards()` retains daily cut and sweep work, then delegates to the reward command with its validated bounds and existing timing values. Row-selection flags are removed because later clicks are unsafe and unnecessary.

**Tech Stack:** Python 3 standard library, `argparse`, `unittest.mock`.

---

### Task 1: Lock in single-claim behavior with focused tests

**Files:**

- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`
- Test: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`

- [ ] **Step 1: Replace the row-parameter test with this single-claim sequence test**

```python
def test_legion_reward_claims_navigates_and_clicks_only_the_single_claim(self) -> None:
    args = zombie_click.build_parser().parse_args(["legion-reward-claims"])
    bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
    clicks: list[tuple[int, int]] = []
    waits: list[float] = []
    with (
        patch.object(zombie_click, "prepare_command_bounds", return_value=bounds),
        patch.object(zombie_click, "perform_click", side_effect=lambda x, y, *_: clicks.append((x, y)) or "mock"),
        patch.object(zombie_click, "sleep_between", side_effect=waits.append),
    ):
        self.assertEqual(zombie_click.command_legion_reward_claims(args), 0)
    point = lambda name: zombie_click.scale_point(zombie_click.ACTIONS[name], bounds)
    self.assertEqual(clicks, [
        point("legion_tab"), point("legion_foreign_challenge"),
        point("legion_reward_left"), point("legion_reward_claim_top"),
        point("legion_reward_popup_dismiss"),
    ])
    self.assertEqual(waits, [4.0, 1.0])
```

- [ ] **Step 2: Add parser rejection and daily-delegation coverage**

```python
def test_legion_reward_claims_has_no_row_selection_flags(self) -> None:
    with self.assertRaises(SystemExit):
        zombie_click.build_parser().parse_args(["legion-reward-claims", "--rows", "1"])

def test_legion_daily_rewards_delegates_reward_claims_after_sweeps(self) -> None:
    args = zombie_click.build_parser().parse_args(["legion-daily-rewards"])
    bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
    with (
        patch.object(zombie_click, "prepare_command_bounds", return_value=bounds),
        patch.object(zombie_click, "perform_click", return_value="mock"),
        patch.object(zombie_click, "run_repeated_click_flow", return_value="mock"),
        patch.object(zombie_click, "command_legion_reward_claims", return_value=0) as claims,
    ):
        self.assertEqual(zombie_click.command_legion_daily_rewards(args), 0)
    delegated = claims.call_args.args[0]
    self.assertIs(delegated.mock_bounds, bounds)
    self.assertEqual(delegated.reward_page_wait, args.reward_page_wait)
    self.assertEqual(delegated.reward_wait, args.reward_wait)
```

- [ ] **Step 3: Run the focused suite**

Run: `python3 -m unittest scripts/test_zombie_click.py -v`

Expected: FAIL because row flags are still accepted and the daily handler still owns reward clicks.

### Task 2: Make `legion-reward-claims` the one-click owner

**Files:**

- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py:1184-1229`

- [ ] **Step 1: Replace row validation and loops with scaled named points and this dry-run**

```python
def command_legion_reward_claims(args: argparse.Namespace) -> int:
    bounds = prepare_command_bounds(args)
    points = scaled_points(bounds, "legion_tab", "legion_foreign_challenge", "legion_reward_left", "legion_reward_claim_top", "legion_reward_popup_dismiss")
    if args.dry_run:
        print("legion reward claims dry-run: " f"reward_page_wait={args.reward_page_wait}, reward_wait={args.reward_wait}, points={points}")
        return 0
```

- [ ] **Step 2: Implement the one-claim navigation and dismissal sequence**

```python
    for action, message, wait in (
        ("legion_tab", "clicked legion tab", 0),
        ("legion_foreign_challenge", "clicked foreign challenge", 0),
        ("legion_reward_left", "clicked rewards tab", args.reward_page_wait),
        ("legion_reward_claim_top", "clicked all-rewards claim", args.reward_wait),
        ("legion_reward_popup_dismiss", "clicked reward-dismiss", 0),
    ):
        backend = perform_click(*points[action], args.backend, bounds)
        print(f"legion reward claims: {message} via {backend}", flush=True)
        sleep_between(wait)
    print(f"legion reward claims complete: attempted one all-rewards claim via {backend}")
    return 0
```

- [ ] **Step 3: Replace parser options with only timing, backend, and dry-run options**

```python
legion_reward_parser = sub.add_parser("legion-reward-claims", help="claim all visible direct-free legion rewards with the verified first claim button")
legion_reward_parser.add_argument("--reward-page-wait", type=non_negative_float, default=4.0)
legion_reward_parser.add_argument("--reward-wait", type=non_negative_float, default=1.0)
legion_reward_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
legion_reward_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
legion_reward_parser.set_defaults(func=command_legion_reward_claims)
```

- [ ] **Step 4: Run the focused suite**

Run: `python3 -m unittest scripts/test_zombie_click.py -v`

Expected: PASS.

### Task 3: Delegate daily legion rewards and document the behavior

**Files:**

- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py:1105-1181`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/SKILL.md`

- [ ] **Step 1: Delete duplicated terminal reward clicks from `command_legion_daily_rewards()` and delegate after sweeps**

```python
    claim_args = argparse.Namespace(
        mock_bounds=bounds, backend=args.backend, dry_run=args.dry_run,
        reward_page_wait=args.reward_page_wait, reward_wait=args.reward_wait,
    )
    command_legion_reward_claims(claim_args)
    print("legion daily rewards complete: attempted daily cut, sweeps, and one all-rewards claim")
    return 0
```

- [ ] **Step 2: Replace multi-row usage examples and guidance in `SKILL.md`**

Document only `legion-reward-claims`, explain it clicks the first direct-free claim once to collect all available rewards, and explicitly prohibit later-row clicks.

- [ ] **Step 3: Run mock dry-runs and complete validation**

Run: `python3 scripts/zombie_click.py --mock-bounds 2,33,508,949 legion-reward-claims --dry-run && python3 scripts/zombie_click.py --mock-bounds 2,33,508,949 legion-daily-rewards --dry-run && python3 -m py_compile scripts/zombie_click.py && python3 -m unittest discover -s scripts -p 'test_zombie_click.py' -v && python3 /Users/paul/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/paul/.codex/skills/zombie-fire-daily && git diff --check`

Expected: every command exits 0, and reward dry-run reports one claim point.

- [ ] **Step 4: Commit only implementation, test, and relevant documentation files**

```bash
git add SKILL.md scripts/zombie_click.py scripts/test_zombie_click.py
git commit -m "refactor: centralize legion reward claims"
```
