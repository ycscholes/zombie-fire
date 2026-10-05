# Standalone Training Hall Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add independent CLI commands for Global Rescue, Terminal Crisis, Battlefield Contest, and Element Trial while preserving the composite training-hall route.

**Architecture:** Extract each existing route block from `command_base_training_hall()` into a helper that accepts `args`, calibrated `points`, and `bounds`. The composite command and four standalone command handlers call the same helpers. Register the handlers through the existing `_TASK_HANDLERS`, `_task_call` wrappers, and argparse patterns.

**Tech Stack:** Python 3, argparse, existing calibrated actions and `zombie_common` click/drag helpers.

---

## Files to change

- `scripts/zombie_tasks/base.py`: route helpers and four standalone command handlers.
- `scripts/zombie_click.py`: compatibility handler map, wrapper functions, and argparse subcommands.
- `scripts/README.md`: command list, prerequisites, and route summaries.
- `SKILL.md`: command examples and training-hall usage notes.

## Task 1: Extract the four existing routes into shared helpers

**Files:**
- Modify: `scripts/zombie_tasks/base.py`

- [x] **Step 1: Add the Global Rescue helper.** Move the existing parent sequence without changing the order or action flags:

```python
def _run_global_rescue_subtask(args, points, bounds):
    _click_action(args, points, "global_rescue_challenge", bounds)
    _click_action(args, points, "global_rescue_free", bounds, reward=True)
    _click_action(args, points, "training_reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "training_hall_back", bounds)
```

- [x] **Step 2: Add the Terminal Crisis helper.** Preserve the current scroll, actions, explicit 0.5-second business wait, and return action:

```python
def _run_terminal_crisis_subtask(args, points, bounds):
    scroll_to_bottom(args)
    if not getattr(args, "skip_scroll", False):
        print("base training hall: scroll_to_bottom (scrolled) via cgclick", flush=True)
    _click_action(args, points, "terminal_crisis_challenge", bounds)
    _click_action(args, points, "terminal_crisis_sweep", bounds)
    _click_action(args, points, "terminal_crisis_confirm", bounds, reward=True)
    _click_action(args, points, "training_reward_dismiss", bounds, dismiss=True)
    sleep_between(0.5)
    _click_action(args, points, "training_hall_back", bounds)
```

- [x] **Step 3: Add the Battlefield Contest helper.** Preserve the current challenge and castle actions, modal drag, `args.battle_times` sweep/dismiss cycles, and modal/back actions:

```python
def _run_battlefield_contest_subtask(args, points, bounds):
    _click_action(args, points, "battle_challenge", bounds)
    _click_action(args, points, "battle_castle", bounds)
    _click_action(args, points, "reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "battle_modal_challenge", bounds)
    scroll_to_bottom(args, "battle_modal_drag_start", "battle_modal_drag_end")
    if not getattr(args, "skip_scroll", False):
        print("base training hall: battle_modal_scroll_to_bottom (scrolled) via cgclick", flush=True)
    for index in range(args.battle_times):
        _click_action(args, points, "battle_sweep_last", bounds, reward=True)
        _click_action(args, points, "battle_reward_dismiss", bounds, dismiss=True)
        print(f"base training hall: battlefield sweep {index + 1}/{args.battle_times} complete", flush=True)
    _click_action(args, points, "battle_modal_close", bounds)
    _click_action(args, points, "training_hall_back", bounds)
```

- [x] **Step 4: Add the Element Trial helper.** Preserve the idle claim, one ten-time sweep, popup dismissals, and back sequence:

```python
def _run_element_trial_subtask(args, points, bounds):
    _click_action(args, points, "element_challenge", bounds)
    _click_action(args, points, "core_trial", bounds)
    _click_action(args, points, "idle_button", bounds)
    _click_action(args, points, "idle_claim", bounds, reward=True)
    _click_action(args, points, "reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "idle_cancel", bounds)
    _click_action(args, points, "core_sweep", bounds)
    _click_action(args, points, "core_sweep_ten", bounds, reward=True)
    _click_action(args, points, "reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "core_sweep_close", bounds)
    _click_action(args, points, "core_trial_back", bounds)
    _click_action(args, points, "element_back", bounds)
```

- [x] **Step 5: Replace the four inline blocks in `command_base_training_hall()` with calls to these helpers in the same order:** Global Rescue, Deep Abyss, Terminal Crisis, Battlefield Contest, Element Trial, then Play Shop. Keep the existing cafeteria sequence, `--battle-times` guard, dry-run output, point list, final back action, and summary unchanged.

## Task 2: Add four standalone command handlers and CLI entries

**Files:**
- Modify: `scripts/zombie_tasks/base.py`
- Modify: `scripts/zombie_click.py`

- [x] **Step 1: Add a shared command wrapper and four handlers in `base.py`.** The wrapper centralizes window preparation, action-point scaling, dry-run, and completion logging:

```python
def _command_training_hall_subtask(args, label, action_names, route, *, scroll_hall_to_bottom=False):
    bounds = prepare_command_bounds(args)
    args.active_bounds = bounds
    points = scaled_points(bounds, *action_names)
    if args.dry_run:
        print(f"{label} subtask dry-run: points={points}")
        return 0
    if scroll_hall_to_bottom:
        scroll_to_bottom(args)
        print("base training hall: scroll_to_bottom (scrolled) via cgclick", flush=True)
    route(args, points, bounds)
    print(f"{label} subtask complete: returned to training hall", flush=True)
    return 0


def command_base_training_hall_global_rescue(args):
    return _command_training_hall_subtask(
        args, "Global Rescue",
        ("global_rescue_challenge", "global_rescue_free", "training_reward_dismiss", "training_hall_back"),
        _run_global_rescue_subtask,
    )


def command_base_training_hall_terminal_crisis(args):
    return _command_training_hall_subtask(
        args, "Terminal Crisis",
        ("terminal_crisis_challenge", "terminal_crisis_sweep", "terminal_crisis_confirm", "training_reward_dismiss", "training_hall_back"),
        _run_terminal_crisis_subtask,
    )


def command_base_training_hall_battlefield_contest(args):
    if args.battle_times < 1:
        raise ClickError("--battle-times must be >= 1")
    return _command_training_hall_subtask(
        args, "Battlefield Contest",
        ("battle_challenge", "battle_castle", "reward_dismiss", "battle_modal_challenge", "battle_sweep_last", "battle_reward_dismiss", "battle_modal_close", "training_hall_back"),
        _run_battlefield_contest_subtask,
        scroll_hall_to_bottom=True,
    )


def command_base_training_hall_element_trial(args):
    return _command_training_hall_subtask(
        args, "Element Trial",
        ("element_challenge", "core_trial", "idle_button", "idle_claim", "reward_dismiss", "idle_cancel", "core_sweep", "core_sweep_ten", "core_sweep_close", "core_trial_back", "element_back"),
        _run_element_trial_subtask,
        scroll_hall_to_bottom=True,
    )
```

The helper point lists include every fixed click and exclude drag start/end actions because `scroll_to_bottom()` resolves those registered actions through `args.active_bounds`. No command enters from the base tab or opens the training hall.

- [x] **Step 2: Register all four handlers in `_TASK_HANDLERS` and define top-level wrappers.** Follow the existing pattern exactly:

```python
"command_base_training_hall_global_rescue": _base.command_base_training_hall_global_rescue,

def command_base_training_hall_global_rescue(args):
    return _task_call(_base, "command_base_training_hall_global_rescue", args)
```

Repeat that pairing for `terminal_crisis`, `battlefield_contest`, and `element_trial`; this makes the existing dependency synchronization apply to each command.

- [x] **Step 3: Add argparse subcommands.** Each command accepts `--backend` and `--dry-run`. Battlefield Contest also accepts `--battle-times` as an integer with default `5`, and validates that it is at least `1` in its handler. Use these exact CLI names:

```text
base-training-hall-global-rescue
base-training-hall-terminal-crisis
base-training-hall-battlefield-contest
base-training-hall-element-trial
```

Set each parser's `func` to its matching wrapper. Do not add `--skip-scroll` to the standalone commands. Terminal Crisis scrolls within its route; Battlefield Contest and Element Trial scroll the hall list before their routes; Global Rescue uses its current list position.

## Task 3: Update command documentation

**Files:**
- Modify: `scripts/README.md`
- Modify: `SKILL.md`

- [x] **Step 1: Add each exact CLI command to the command examples in both files.** Keep the existing Deep Abyss and Play Shop command examples.
- [x] **Step 2: Document the common start and finish page.** State that all four commands begin on the open Training Hall list page and return there. Note Terminal Crisis, Battlefield Contest, and Element Trial scroll the list to the bottom when needed. Summarize each route and state that Battlefield Contest defaults to five sweeps and accepts `--battle-times`.
- [x] **Step 3: Preserve the existing free-action and no-live-proof boundaries.** State that the routes reuse the current fixed actions and do not refill attempts or add purchases, ads, or ambiguous actions.

## Review checklist

- The four standalone routes use the same helper functions as the composite command.
- The composite order and existing action/wait sequence remain unchanged.
- Each standalone command's dry-run path returns before any click or drag.
- All prior unrelated working-tree changes remain unstaged and unmodified.
- No tests are added or run for this request, as specified by the approved design.
