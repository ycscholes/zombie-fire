# Command Focus Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Focus the game window before every window-operating helper command, while keeping inspection, simulation, and help usage independent of a game window.

**Architecture:** Add a single command-classification predicate next to the CLI entry point in `zombie_click.py`. `main()` will parse arguments, reject invalid real mock executions as it does today, call the focus helper only when the predicate identifies an operating subcommand, then dispatch to the selected handler. Tests import the script module without invoking its CLI entry point and exercise the predicate only.

**Tech Stack:** Python 3 standard library (`argparse`, `unittest`); macOS `osascript` remains behind the existing focus helper.

---

## File structure

- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py` — centralize the decision whether a parsed command must focus the game window before dispatch.
- Create: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py` — isolated `unittest` coverage for the command-classification predicate, with no macOS UI calls.

### Task 1: Define and test focus eligibility

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py:1161`
- Create: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`

- [ ] **Step 1: Write the failing test**

```python
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).with_name("zombie_click.py")
SPEC = importlib.util.spec_from_file_location("zombie_click", SCRIPT)
zombie_click = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(zombie_click)


class FocusEligibilityTests(unittest.TestCase):
    def test_non_operating_commands_do_not_focus(self) -> None:
        for command in ("list", "state", "self-test", "dry-run"):
            self.assertFalse(zombie_click.command_requires_focus(command))

    def test_operating_commands_focus(self) -> None:
        for command in ("bounds", "fit-window", "click", "seq", "mail-claim"):
            self.assertTrue(zombie_click.command_requires_focus(command))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v`

Expected: FAIL because `command_requires_focus` does not exist.

- [ ] **Step 3: Implement the predicate and use it at dispatch**

```python
NON_OPERATING_COMMANDS = frozenset({"list", "state", "self-test", "dry-run"})


def command_requires_focus(command: str) -> bool:
    return command not in NON_OPERATING_COMMANDS


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if (
            getattr(args, "mock_bounds", None)
            and not getattr(args, "dry_run", False)
            and args.command not in {"bounds", "dry-run", "list", "state", "self-test"}
        ):
            raise ClickError("--mock-bounds is simulation-only; add --dry-run instead of executing clicks")
        if command_requires_focus(args.command):
            focus_game_window_at_start()
        return args.func(args)
```

Keep the existing mock-bounds safety condition unchanged; the predicate is only responsible for the focus decision. `--help` exits inside `argparse` before `main()` can dispatch a parsed command.

- [ ] **Step 4: Run the focused unit test**

Run: `python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v`

Expected: PASS with both focus-eligibility tests passing.

- [ ] **Step 5: Commit if the skill directory is a Git worktree**

Run: `git -C /Users/paul/.codex/skills/zombie-fire-daily status --short`

Expected: This checkout is currently not a Git worktree, so record the changed files without attempting a commit.

### Task 2: Verify CLI behavior without UI clicks

**Files:**
- Modify: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py`
- Test: `/Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`

- [ ] **Step 1: Run Python syntax validation**

Run: `python3 -m py_compile /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py /Users/paul/.codex/skills/zombie-fire-daily/scripts/test_zombie_click.py`

Expected: exit code 0 and no output.

- [ ] **Step 2: Run an exempt command**

Run: `python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py self-test`

Expected: `self-test ok`; it does not call the focus helper or click any window.

- [ ] **Step 3: Run the helper help path**

Run: `python3 /Users/paul/.codex/skills/zombie-fire-daily/scripts/zombie_click.py --help`

Expected: CLI usage text; `argparse` exits before focus or command dispatch.

- [ ] **Step 4: Run all isolated tests**

Run: `python3 -m unittest discover -s /Users/paul/.codex/skills/zombie-fire-daily/scripts -p 'test_zombie_click.py' -v`

Expected: PASS; the test suite makes no `osascript` call and no UI click.

## Self-review

- Spec coverage: Task 1 implements the central operating-command focus gate, preserves exempt commands, preserves the existing fail-closed mock guard, and retains per-click validation. Task 2 verifies exemption, help, syntax, and the decision logic.
- Placeholder scan: no incomplete tasks or undefined implementation details remain.
- Type consistency: `command_requires_focus` accepts the parsed string `args.command`; all tests pass string command names and import the same function.
