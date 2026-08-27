"""Shop tab training-hall free-reward workflow."""

from __future__ import annotations

from ..zombie_common import *
from ..zombie_actions import *
from .base import scroll_to_bottom as _base_scroll_to_bottom


def scroll_to_bottom(
    args: argparse.Namespace,
    start_action: str = "shop_resource_drag_start",
    end_action: str = "shop_resource_drag_end",
) -> None:
    """Use two long upward drags so the shop's long resource list reaches its end."""
    for _ in range(2):
        _base_scroll_to_bottom(args, start_action, end_action)


def command_shop_training_hall(args: argparse.Namespace) -> int:
    """Claim the two explicitly free gold cards in the shop route."""
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
        print(f"shop training hall dry-run: points={points}")
        return 0

    backend = perform_click(*points["shop_tab"], args.backend, bounds)
    print(f"shop training hall: opened shop tab via {backend}", flush=True)
    backend = perform_click(*points["shop_resource_tab"], args.backend, bounds)
    print(f"shop training hall: opened resource tab via {backend}", flush=True)
    scroll_to_bottom(args, "shop_resource_drag_start", "shop_resource_drag_end")
    print("shop training hall: scrolled resource page to bottom via cgclick", flush=True)
    backend = perform_click(*points["shop_resource_gold600_free"], args.backend, bounds)
    print(f"shop training hall: claimed resource gold x600 via {backend}", flush=True)
    backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
    print(f"shop training hall: dismissed resource reward via {backend}", flush=True)
    backend = perform_click(*points["shop_special_pack_tab"], args.backend, bounds)
    print(f"shop training hall: opened special-pack tab via {backend}", flush=True)
    backend = perform_click(*points["shop_gold_free"], args.backend, bounds)
    print(f"shop training hall: claimed special-pack gold via {backend}", flush=True)
    backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
    print(f"shop training hall complete: dismissed special-pack reward via {backend}")
    return 0
