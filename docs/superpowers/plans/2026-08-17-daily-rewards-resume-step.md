# Daily Rewards Resume Step Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `daily-rewards --from-step N` safely resume from any of its five phase boundaries.

**Architecture:** The command keeps one focus/calibration preflight and one shared `Bounds` object. It prepopulates phase-summary entries before the requested index as `skipped`, then runs the existing phase loop unchanged from that index; no state is persisted and no phase-internal coordinate is resumed.

**Tech Stack:** Python 3 standard library, `argparse`, `unittest`.

---

### Task 1: Lock phase-resume behavior with failing tests

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py:620-770`
- Test: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`

- [ ] **Step 1: Add a test that resumes at welfare and shares the calibrated bounds**

```python
def test_daily_rewards_from_step_three_skips_patrol_and_calendar(self) -> None:
    args = zombie_click.build_parser().parse_args(
        ["--mock-bounds", "2,33,508,949", "daily-rewards", "--from-step", "3", "--dry-run"]
    )
    phases: list[str] = []
    with (
        patch.object(zombie_click, "command_patrol_full_from_home") as patrol,
        patch.object(zombie_click, "command_calendar_claim") as calendar,
        patch.object(zombie_click, "command_welfare_claim", side_effect=lambda _: phases.append("welfare")),
        patch.object(zombie_click, "command_mail_claim", side_effect=lambda _: phases.append("mail")),
        patch.object(zombie_click, "command_legion_daily_rewards", side_effect=lambda _: phases.append("legion")),
        patch("builtins.print") as print_mock,
    ):
        self.assertEqual(zombie_click.command_daily_rewards(args), 0)

    patrol.assert_not_called()
    calendar.assert_not_called()
    self.assertEqual(phases, ["welfare", "mail", "legion"])
    summary = "\n".join(str(call.args[0]) for call in print_mock.call_args_list)
    self.assertIn("patrol=skipped", summary)
    self.assertIn("calendar=skipped", summary)
```

- [ ] **Step 2: Add parser tests for valid default and invalid step bounds**

```python
def test_daily_rewards_from_step_defaults_to_one(self) -> None:
    args = zombie_click.build_parser().parse_args(["daily-rewards"])
    self.assertEqual(args.from_step, 1)

def test_daily_rewards_from_step_rejects_out_of_range_values(self) -> None:
    for value in ("0", "6"):
        with self.subTest(value=value), self.assertRaises(SystemExit):
            zombie_click.build_parser().parse_args(["daily-rewards", "--from-step", value])
```

- [ ] **Step 3: Run the tests and verify they fail because `--from-step` is unrecognized**

Run: `python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v`

Expected: the new resume test fails during argument parsing with `unrecognized arguments: --from-step 3`.

### Task 2: Add bounded resume parameter and phase skipping

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py:1207-1272`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py:1582-1589`
- Test: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py:620-770`

- [ ] **Step 1: Add the parser argument with a fixed stage range**

```python
daily_parser.add_argument(
    "--from-step",
    type=int,
    choices=range(1, 6),
    default=1,
    metavar="N",
    help="resume daily rewards at phase 1=patrol, 2=calendar, 3=welfare, 4=mail, or 5=legion",
)
```

- [ ] **Step 2: Prepopulate skipped phases and start the existing loop at the selected index**

```python
from_step = getattr(args, "from_step", 1)
start_index = from_step - 1
results: list[PhaseResult] = [
    PhaseResult(name, "skipped") for name, _ in phases[:start_index]
]
for index, (name, handler) in enumerate(phases[start_index:], start=start_index):
    print(f"daily rewards: starting step {index + 1} {name}", flush=True)
    # Keep the existing run_daily_phase, typed recovery, fatal summary, and re-raise behavior.
```

- [ ] **Step 3: Run focused tests and verify all pass**

Run: `python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v`

Expected: exit 0; step 3 calls only welfare, mail, legion and summary includes patrol/calendar `skipped`.

### Task 3: Document and validate the public resume command

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/SKILL.md:20-21`
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/SKILL.md:184-210`

- [ ] **Step 1: Add the public usage example and phase map**

```markdown
python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py daily-rewards --from-step 3
```

Document that `1=patrol`, `2=calendar`, `3=welfare`, `4=mail`, `5=legion`; the option starts a new preflighted run at that phase, does not infer prior progress, and never resumes a phase-internal click.

- [ ] **Step 2: Compile and dry-run a step-3 resume**

Run: `python3 -m py_compile /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py && python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py --mock-bounds 2,33,508,949 daily-rewards --from-step 3 --dry-run`

Expected: exit 0 and summary containing `patrol=skipped`, `calendar=skipped`, then completed simulated welfare/mail/legion phases.

- [ ] **Step 3: Validate the packaged skill and exact diff**

Run: `python3 /Users/paul/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/paul/.codex/skills/zombie-fire-daily && git -C /Users/paul/.codex/skills/zombie-fire-daily diff --check`

Expected: `Skill is valid!` and no diff-check output.

- [ ] **Step 4: Commit only files owned by this feature**

Run: `git -C /Users/paul/.codex/skills/zombie-fire-daily add scripts/zombie_click.py scripts/test_zombie_click.py SKILL.md docs/superpowers/specs/2026-08-17-daily-rewards-resume-step-design.md docs/superpowers/plans/2026-08-17-daily-rewards-resume-step.md && git -C /Users/paul/.codex/skills/zombie-fire-daily commit -m "feat: resume daily rewards by step"`

Expected: commit excludes the unrelated pre-existing untracked documents and previously modified files.
