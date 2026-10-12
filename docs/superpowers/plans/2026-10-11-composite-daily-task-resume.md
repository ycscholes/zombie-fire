# Composite Daily Task Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a named `--from-task` selector to every multi-task daily orchestrator so a run starts at a chosen business-task boundary and continues through the remaining route.

**Architecture:** A shared task selector validates stable task IDs and builds the skipped/remaining task lists. Each route owns its task table and retains its existing action functions, waits, recovery, and page assumptions; `daily-rewards` maps qualified IDs into a phase plus a local task selector while preserving `--from-step`.

**Tech Stack:** Python 3, argparse, existing `zombie_click.py` task modules.

---

## Files and responsibilities

- Create `scripts/zombie_tasks/resume.py` for named task selection, validation, and concise task-plan output.
- Modify `scripts/zombie_click.py` to expose `--from-task` for supported composite commands and make it mutually exclusive with `daily-rewards --from-step`.
- Modify `scripts/zombie_tasks/daily.py`, `patrol.py`, `journey.py`, `legion.py`, `base.py`, and `shop.py` to split orchestration at the task IDs in the approved spec and run the selected suffix.
- Update `SKILL.md` and `scripts/README.md` with task ID tables, examples, and required starting pages.
- Preserve all unrelated working-tree modifications, including the existing temporary comment for `legion_journey_go`.

## Task 1: Add the shared named-task selector

**Files:**
- Create: `scripts/zombie_tasks/resume.py`

- [x] Define `TaskSelection` with `skipped: tuple[str, ...]` and `remaining: tuple[str, ...]`.
- [x] Implement `select_task_suffix(task_ids, from_task, scope)`: return all IDs when `from_task is None`; otherwise locate the exact ID, return its prefix as skipped and its suffix as remaining, and raise `ClickError` for an unknown ID before callers begin clicking.
- [x] Implement a renderer that prints the selector scope, skipped IDs, selected ID, and remaining IDs for dry-run and resume logs.
- [x] Put the approved daily and local ID tuples in this module so CLI choices, task runners, and docs use one source of truth.

The shared interface is:

```python
@dataclass(frozen=True)
class TaskSelection:
    skipped: tuple[str, ...]
    remaining: tuple[str, ...]


def select_task_suffix(
    task_ids: Sequence[str], from_task: str | None, scope: str
) -> TaskSelection:
    ...
```

## Task 2: Add selectors to Journey, shop, and patrol routes

**Files:**
- Modify: `scripts/zombie_tasks/journey.py`
- Modify: `scripts/zombie_tasks/shop.py`
- Modify: `scripts/zombie_tasks/patrol.py`

- [x] `command_journey_daily_rewards` runs `resources` and then `purifier`; selecting `purifier` skips only resource claims.
- [x] `command_shop_training_hall` separates `resource_gold` from `special_pack_gold`; selecting the second skips the resource-page claim and begins from the special-pack entry page.
- [x] `command_patrol_full_from_home` exposes `claim`, `quick_patrol`, and `ad_patrol` boundaries. The selected task starts from its documented page and later batches keep their current configured counts.
- [x] Keep standalone single-business Journey commands atomic; their existing multiple clicks remain one task.
- [x] Each route validates its selector before its first click and prints skipped/remaining tasks in dry-run output.

## Task 3: Add selectors to Base and training-hall shop routes

**Files:**
- Modify: `scripts/zombie_tasks/base.py`

- [x] Refactor `command_base_training_hall` into the named sequence `cafeteria`, `global_rescue`, `global_expedition`, `deep_abyss`, `terminal_crisis`, `battlefield_contest`, `element_trial`, `play_shop` without changing task order, waits, scroll behavior, or return navigation.
- [x] Add local IDs for the currently enabled `base_powder`, `gun_blueprint`, and `base_materials` actions to `command_base_training_hall_shop`.
- [x] Retain existing standalone one-task commands and reuse the existing subtask functions where they already match the composite route.
- [x] Start after the chosen boundary without replaying the preceding `base_tab`, cafeteria, challenge, or shop actions; document the required open page for each task ID.

## Task 4: Add selectors to Legion routes

**Files:**
- Modify: `scripts/zombie_tasks/legion.py`

- [x] Refactor `command_legion_daily_rewards` into `daily_cut`, `foreign_rewards`, `shop`, and `journey_gifts`, retaining the order and existing shared `Bounds` behavior.
- [x] Add `sweeps`, `legion_rewards`, and `personal_rewards` boundaries to `command_legion_reward_claims`.
- [x] Add `gun_blueprint`, `base_powder`, and `enhancer` boundaries to `command_legion_shop_purchases`.
- [x] Add `gift_claim` and `expedition` boundaries to `command_legion_journey_gifts`; keep the `legion_journey_go` action out of the runtime sequence as the user requested.
- [x] Validate IDs before clicks and make dry-run output show the skipped and remaining task names.

## Task 5: Add global task selection to the daily orchestrator and CLI

**Files:**
- Modify: `scripts/zombie_tasks/daily.py`
- Modify: `scripts/zombie_click.py`

- [x] Add the approved qualified daily IDs to `daily-rewards`; when an ID has a phase prefix, skip earlier phases and pass the suffix ID to that phase handler.
- [x] Continue all later phases after the selected phase completes. Print skipped phase/task IDs and the selected task in the summary.
- [x] Preserve `--from-step 1..8`; reject using `--from-step` with `--from-task` during argparse validation.
- [x] Add local `--from-task` choices to `patrol-full-from-home`, `journey-daily-rewards`, `base-training-hall`, `base-training-hall-shop`, `shop-training-hall`, `legion-daily-rewards`, `legion-reward-claims`, `legion-shop-purchases`, and `legion-journey-gifts`.
- [x] Keep task ID validation and selector logging before the first operation that can click or drag.

## Task 6: Update operator documentation and inspect the final diff

**Files:**
- Modify: `SKILL.md`
- Modify: `scripts/README.md`

- [x] Add examples for global nested resume and local command resume, including `daily-rewards --from-task legion.shop_purchases`, `legion-daily-rewards --from-task shop`, and `base-training-hall --from-task element_trial`.
- [x] Document each accepted ID, its required game entry page, behavior for skipped tasks, and the limitation that a selected repeated batch runs from its first iteration at its configured count.
- [x] Document that `--from-step` remains the eight-phase shortcut and is mutually exclusive with `--from-task`.
- [x] Centralize required entry-page metadata and show it in CLI help and explicit resume plans, including patrol JSON dry-run output.
- [x] Scroll the training-hall list before a directly resumed Battlefield Contest or Element Trial; retain `--skip-scroll` as the operator override and document its bottom-of-list precondition.
- [x] Reset inherited `skip_scroll` for the nested play-shop route so its item and tab navigation keep the original behavior.
- [x] Run Python compilation for changed Python modules and `git diff --check`; do not run gameplay commands or unit tests unless the user requests verification.
- [x] Review the final diff to confirm the task order, existing action coordinates, waits, recovery logic, and user changes are preserved.

## Completion contract

- Every ID in the approved spec is exposed in the correct daily or local command scope.
- A selected task runs with every later task in its orchestration; earlier tasks are reported skipped.
- Invalid selectors and incompatible options fail before clicks or drags.
- Existing defaults and `--from-step` behavior remain unchanged.
- Python compilation and diff inspection complete; no live game action is performed.
