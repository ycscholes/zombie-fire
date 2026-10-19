"""商城免费金币领取任务。"""

from __future__ import annotations

from ..zombie_common import *
from ..zombie_actions import *
from .base import scroll_to_bottom as _base_scroll_to_bottom
from .resume import (
    LOCAL_TASK_IDS,
    print_task_selection,
    report_desktop_task,
    select_enabled_task_suffix,
)


def scroll_to_bottom(
    args: argparse.Namespace,
    start_action: str = "shop_resource_drag_start",
    end_action: str = "shop_resource_drag_end",
) -> None:
    """商城列表：连续向上拖动两次，使资源列表滚动到底部。"""
    for _ in range(2):
        _base_scroll_to_bottom(args, start_action, end_action)


def command_shop_training_hall(args: argparse.Namespace) -> int:
    """商城免费奖励：领取资源页和特惠礼包页的免费金币。"""
    selection = select_enabled_task_suffix(
        LOCAL_TASK_IDS["shop-training-hall"],
        getattr(args, "from_task", None),
        "shop-training-hall",
        getattr(args, "desktop_task_ids", None),
    )
    print_task_selection("shop-training-hall", selection, dry_run=args.dry_run)
    bounds = prepare_command_bounds(args)
    args.active_bounds = bounds
    points = scaled_points(
        bounds,
        "shop_tab",
        "shop_resource_tab",
        "shop_resource_drag_start",
        "shop_resource_drag_end",
        "shop_resource_gold600_free",
        "reward_dismiss",
        "shop_special_pack_tab",
        "shop_gold_free",
    )
    if args.dry_run:
        print(f"shop training hall dry-run: tasks={selection.remaining}, skipped={selection.skipped}, points={points}")
        for task_id in selection.remaining:
            report_desktop_task(args, task_id, "started")
            report_desktop_task(args, task_id, "completed")
        return 0

    if "resource_gold" in selection.remaining:
        report_desktop_task(args, "resource_gold", "started")
        backend = perform_tab_click(*points["shop_tab"], args.backend, bounds)
        print(f"shop training hall: opened shop tab via {backend}", flush=True)
        backend = perform_click(*points["shop_resource_tab"], args.backend, bounds)
        print(f"shop training hall: opened resource tab via {backend}", flush=True)
        scroll_to_bottom(args, "shop_resource_drag_start", "shop_resource_drag_end")
        print("shop training hall: scrolled resource page to bottom via cgclick", flush=True)
        backend = perform_reward_click(*points["shop_resource_gold600_free"], args.backend, bounds)
        print(f"shop training hall: claimed resource gold x600 via {backend}", flush=True)
        backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
        print(f"shop training hall: dismissed resource reward via {backend}", flush=True)
        report_desktop_task(args, "resource_gold", "completed")
    if "special_pack_gold" in selection.remaining:
        report_desktop_task(args, "special_pack_gold", "started")
        if getattr(args, "desktop_navigate_shop_special", False):
            backend = perform_tab_click(*points["shop_tab"], args.backend, bounds)
            print(f"shop training hall: opened shop tab for selected special-pack task via {backend}", flush=True)
            backend = perform_click(*points["shop_special_pack_tab"], args.backend, bounds)
            print(f"shop training hall: opened special-pack tab without claiming resource gold via {backend}", flush=True)
        if "resource_gold" in selection.remaining:
            backend = perform_click(*points["shop_special_pack_tab"], args.backend, bounds)
            print(f"shop training hall: opened special-pack tab via {backend}", flush=True)
        backend = perform_reward_click(*points["shop_gold_free"], args.backend, bounds)
        print(f"shop training hall: claimed special-pack gold via {backend}", flush=True)
        backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
        print(f"shop training hall complete: dismissed special-pack reward via {backend}")
        report_desktop_task(args, "special_pack_gold", "completed")
    return 0
