"""Shared named-task selectors for resumable daily workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..zombie_common import ClickError


DAILY_TASK_IDS = (
    "patrol.claim",
    "patrol.quick_patrol",
    "patrol.ad_patrol",
    "calendar",
    "welfare",
    "mail",
    "legion.daily_cut",
    "legion.foreign_rewards",
    "legion.shop_purchases",
    "legion.journey_gifts",
    "journey.resources",
    "journey.purifier",
    "base.cafeteria",
    "base.global_rescue",
    "base.global_expedition",
    "base.deep_abyss",
    "base.terminal_crisis",
    "base.battlefield_contest",
    "base.element_trial",
    "base.play_shop",
    "shop.resource_gold",
    "shop.special_pack_gold",
)

LOCAL_TASK_IDS = {
    "patrol-full-from-home": ("claim", "quick_patrol", "ad_patrol"),
    "legion-daily-rewards": ("daily_cut", "foreign_rewards", "shop", "journey_gifts"),
    "journey-daily-rewards": ("resources", "purifier"),
    "base-training-hall": (
        "cafeteria", "global_rescue", "global_expedition", "deep_abyss", "terminal_crisis",
        "battlefield_contest", "element_trial", "play_shop",
    ),
    "shop-training-hall": ("resource_gold", "special_pack_gold"),
    "legion-reward-claims": ("sweeps", "legion_rewards", "personal_rewards"),
    "legion-shop-purchases": ("gun_blueprint", "base_powder", "enhancer"),
    "legion-journey-gifts": ("gift_claim", "expedition"),
    "base-training-hall-shop": ("base_powder", "gun_blueprint", "base_materials"),
}

DAILY_TASK_ENTRY_PAGES = {
    "patrol.claim": "首页",
    "patrol.quick_patrol": "巡逻面板",
    "patrol.ad_patrol": "巡逻面板",
    "calendar": "首页",
    "welfare": "首页",
    "mail": "首页",
    "legion.daily_cut": "首页",
    "legion.foreign_rewards": "首页",
    "legion.shop_purchases": "军团页",
    "legion.journey_gifts": "军团页",
    "journey.resources": "首页",
    "journey.purifier": "首页",
    "base.cafeteria": "基地页",
    "base.global_rescue": "训练大厅列表",
    "base.global_expedition": "训练大厅列表",
    "base.deep_abyss": "训练大厅列表",
    "base.terminal_crisis": "训练大厅列表",
    "base.battlefield_contest": "训练大厅列表（执行时滚到底部）",
    "base.element_trial": "训练大厅列表（执行时滚到底部）",
    "base.play_shop": "训练大厅列表",
    "shop.resource_gold": "首页",
    "shop.special_pack_gold": "商城特惠礼包页",
}

# Local IDs can repeat across commands, so page requirements are keyed by scope.
LOCAL_TASK_ENTRY_PAGES = {
    "patrol-full-from-home": {
        "claim": "首页",
        "quick_patrol": "巡逻面板",
        "ad_patrol": "巡逻面板",
    },
    "legion-daily-rewards": {
        "daily_cut": "首页",
        "foreign_rewards": "首页",
        "shop": "军团页",
        "journey_gifts": "军团页",
    },
    "journey-daily-rewards": {"resources": "首页", "purifier": "首页"},
    "base-training-hall": {
        "cafeteria": "基地页",
        "global_rescue": "训练大厅列表",
        "global_expedition": "训练大厅列表",
        "deep_abyss": "训练大厅列表",
        "terminal_crisis": "训练大厅列表",
        "battlefield_contest": "训练大厅列表（默认执行前滚到底部；--skip-scroll 时须已在底部）",
        "element_trial": "训练大厅列表（默认执行前滚到底部；--skip-scroll 时须已在底部）",
        "play_shop": "训练大厅列表",
    },
    "shop-training-hall": {
        "resource_gold": "首页",
        "special_pack_gold": "商城特惠礼包页",
    },
    "legion-reward-claims": {
        "sweeps": "首页",
        "legion_rewards": "异域挑战页",
        "personal_rewards": "军团奖励面板",
    },
    "legion-shop-purchases": {
        "gun_blueprint": "军团商店列表并滚到枪械图纸",
        "base_powder": "军团商店列表并滚到基建粉末",
        "enhancer": "军团商店列表并滚到强化剂",
    },
    "legion-journey-gifts": {
        "gift_claim": "军团页",
        "expedition": "征途礼物页",
    },
    "base-training-hall-shop": {
        "base_powder": "玩法商店强化剂页",
        "gun_blueprint": "玩法商店枪械图纸页",
        "base_materials": "玩法商店基建耗材页",
    },
}

# Each daily selector maps to a phase and, where that phase is itself a composite,
# to the phase-local task ID accepted by its handler.
DAILY_TASK_TARGETS = {
    "patrol.claim": ("patrol", "claim"),
    "patrol.quick_patrol": ("patrol", "quick_patrol"),
    "patrol.ad_patrol": ("patrol", "ad_patrol"),
    "calendar": ("calendar", None),
    "welfare": ("welfare", None),
    "mail": ("mail", None),
    "legion.daily_cut": ("legion", "daily_cut"),
    "legion.foreign_rewards": ("legion", "foreign_rewards"),
    "legion.shop_purchases": ("legion", "shop"),
    "legion.journey_gifts": ("legion", "journey_gifts"),
    "journey.resources": ("journey", "resources"),
    "journey.purifier": ("journey", "purifier"),
    "base.cafeteria": ("base", "cafeteria"),
    "base.global_rescue": ("base", "global_rescue"),
    "base.global_expedition": ("base", "global_expedition"),
    "base.deep_abyss": ("base", "deep_abyss"),
    "base.terminal_crisis": ("base", "terminal_crisis"),
    "base.battlefield_contest": ("base", "battlefield_contest"),
    "base.element_trial": ("base", "element_trial"),
    "base.play_shop": ("base", "play_shop"),
    "shop.resource_gold": ("shop", "resource_gold"),
    "shop.special_pack_gold": ("shop", "special_pack_gold"),
}


@dataclass(frozen=True)
class TaskSelection:
    skipped: tuple[str, ...]
    remaining: tuple[str, ...]
    explicit_start: bool = False

    @property
    def selected(self) -> str:
        return self.remaining[0]


def select_task_suffix(
    task_ids: Sequence[str], from_task: str | None, scope: str
) -> TaskSelection:
    """Validate a task ID and return the selected task plus the remaining suffix."""
    ids = tuple(task_ids)
    if not ids:
        raise ValueError("task_ids must contain at least one task")
    if from_task is None:
        return TaskSelection((), ids, False)
    try:
        start = ids.index(from_task)
    except ValueError as exc:
        choices = ", ".join(ids)
        raise ClickError(f"unknown --from-task {from_task!r} for {scope}; choose one of: {choices}") from exc
    return TaskSelection(ids[:start], ids[start:], True)


def print_task_selection(scope: str, selection: TaskSelection, *, dry_run: bool) -> None:
    """Print the skipped prefix and the tasks this run will attempt."""
    mode = "dry-run " if dry_run else ""
    skipped = ", ".join(selection.skipped) or "none"
    remaining = ", ".join(selection.remaining)
    entry_page = (
        f", entry_page={task_entry_page(scope, selection.selected)}"
        if selection.explicit_start
        else ""
    )
    print(
        f"{scope} {mode}task plan: skipped=[{skipped}], "
        f"selected={selection.selected}{entry_page}, remaining=[{remaining}]",
        flush=True,
    )


def task_entry_page(scope: str, task_id: str) -> str:
    """Return the documented game page required before starting a task ID."""
    pages = DAILY_TASK_ENTRY_PAGES if scope == "daily-rewards" else LOCAL_TASK_ENTRY_PAGES[scope]
    return pages[task_id]


def task_entry_help(scope: str) -> str:
    """Format accepted IDs with their required starting pages for CLI help."""
    pages = DAILY_TASK_ENTRY_PAGES if scope == "daily-rewards" else LOCAL_TASK_ENTRY_PAGES[scope]
    return "; ".join(f"{task_id}={page}" for task_id, page in pages.items())
