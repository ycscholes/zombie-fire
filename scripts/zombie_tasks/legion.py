"""Legion tab workflows."""

from __future__ import annotations

from ..zombie_common import *
from ..zombie_actions import *

from .base import scroll_to_bottom as _base_scroll_to_bottom

BUSINESS_WAITS = {
    "legion_foreign_challenge": 0.3,
    "legion_sweep": 0.3,
    "legion_sweep_confirm": 0.3,
    "legion_sweep_between": 0.3,
    "legion_reward_left": 0.3,
}


def scroll_legion_shop_to_bottom(args: argparse.Namespace) -> None:
    """Scroll the legion shop list to its bottom using the proven canvas drag."""
    _base_scroll_to_bottom(args, "legion_shop_drag_start", "legion_shop_drag_end")


def _purchase_legion_shop_item(args: argparse.Namespace, points: dict[str, tuple[int, int]], item_action: str, bounds: Bounds) -> None:
    backend = perform_click(*points[item_action], args.backend, bounds)
    print(f"legion shop purchases: opened {item_action} via {backend}", flush=True)
    perform_click(*points["legion_shop_max"], args.backend, bounds)
    perform_reward_click(*points["legion_shop_buy"], args.backend, bounds)
    perform_dismiss_click(*points["legion_shop_reward_dismiss"], args.backend, bounds)
    perform_click(*points["legion_shop_modal_close"], args.backend, bounds)
    print(f"legion shop purchases: completed {item_action}", flush=True)


def command_legion_shop_purchases(args: argparse.Namespace) -> int:
    """Open the legion shop and position its list at the bottom for purchases."""
    bounds = prepare_command_bounds(args)
    args.active_bounds = bounds
    points = scaled_points(
        bounds,
        "legion_shop", "legion_shop_drag_start", "legion_shop_drag_end",
        "legion_shop_gun_blueprint", "legion_shop_base_powder", "legion_shop_enhancer",
        "legion_shop_max", "legion_shop_buy", "legion_shop_reward_dismiss",
        "legion_shop_modal_close", "legion_shop_close",
    )
    if args.dry_run:
        print(f"legion shop purchases dry-run: points={points}")
        return 0

    backend = perform_click(*points["legion_shop"], args.backend, bounds)
    print(f"legion shop purchases: opened shop via {backend}", flush=True)
    scroll_legion_shop_to_bottom(args)
    print("legion shop purchases: scrolled to bottom via cgclick", flush=True)
    for item_action in ("legion_shop_gun_blueprint", "legion_shop_base_powder", "legion_shop_enhancer"):
        _purchase_legion_shop_item(args, points, item_action, bounds)
    perform_click(*points["legion_shop_close"], args.backend, bounds)
    print("legion shop purchases complete: purchased three items and closed shop", flush=True)
    return 0

def command_legion_daily_rewards(args: argparse.Namespace) -> int:
    """Run the verified daily-cut, foreign-sweep, and legion-reward sequence."""
    if args.sweep_times < 1:
        raise ClickError("--sweep-times must be >= 1")
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "legion_tab",
        "legion_daily_cut",
        "legion_cut_once",
        "reward_dismiss",
        "legion_modal_close",
    )
    if args.dry_run:
        print(
            "legion daily rewards dry-run: "
            f"sweep_times={args.sweep_times}, event_waits={BUSINESS_WAITS}, points={points}"
        )
        command_legion_reward_claims(
            argparse.Namespace(
                mock_bounds=bounds,
                backend=args.backend,
                dry_run=True,
                sweep_times=args.sweep_times,
            )
        )
        return 0

    backend = perform_tab_click(*points["legion_tab"], args.backend, bounds)
    set_phase_state(args, "legion_opened")
    print(f"legion daily rewards: clicked legion tab via {backend}", flush=True)
    backend = perform_click(*points["legion_daily_cut"], args.backend, bounds)
    set_phase_state(args, "legion_daily_cut_opened")
    print(f"legion daily rewards: opened daily cut via {backend}", flush=True)
    backend = perform_reward_click(*points["legion_cut_once"], args.backend, bounds)
    print(f"legion daily rewards: clicked daily cut once via {backend}", flush=True)
    backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
    print(f"legion daily rewards: dismissed daily-cut reward info via {backend}", flush=True)
    backend = perform_click(*points["legion_modal_close"], args.backend, bounds)
    print(f"legion daily rewards: closed daily-cut modal via {backend}", flush=True)

    command_legion_reward_claims(
        argparse.Namespace(
            mock_bounds=bounds,
            backend=args.backend,
            dry_run=False,
            sweep_times=args.sweep_times,
            phase_progress=getattr(args, "phase_progress", None),
        )
    )
    command_legion_shop_purchases(
        argparse.Namespace(
            mock_bounds=bounds,
            backend=args.backend,
            dry_run=False,
            phase_progress=getattr(args, "phase_progress", None),
        )
    )
    print("legion daily rewards complete: attempted daily cut, foreign-challenge rewards, and shop purchases")
    return 0
def command_legion_reward_claims(args: argparse.Namespace) -> int:
    if args.sweep_times < 1:
        raise ClickError("--sweep-times must be >= 1")
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "legion_tab",
        "legion_foreign_challenge",
        "legion_sweep",
        "legion_sweep_confirm",
        "legion_reward_popup_dismiss",
        "legion_reward_left",
        "legion_reward_claim_top",
        "reward_dismiss",
        "legion_personal_reward_tab",
        "legion_personal_reward_claim_top",
        "legion_reward_panel_close",
        "legion_foreign_challenge_back",
    )
    if args.dry_run:
        print(
            "legion reward claims dry-run: "
            f"sweep_times={args.sweep_times}, event_waits={BUSINESS_WAITS}, points={points}"
        )
        return 0
    backend = perform_tab_click(*points["legion_tab"], args.backend, bounds)
    set_phase_state(args, "legion_opened")
    print(f"legion reward claims: clicked legion tab via {backend}", flush=True)
    backend = perform_action("legion_foreign_challenge", *points["legion_foreign_challenge"], args.backend, bounds, BUSINESS_WAITS)
    set_phase_state(args, "legion_foreign_challenge_opened")
    print(f"legion reward claims: clicked foreign challenge via {backend}", flush=True)
    run_repeated_click_flow(
        points={
            "sweep": points["legion_sweep"],
            "confirm": points["legion_sweep_confirm"],
            "dismiss": points["legion_reward_popup_dismiss"],
        },
        bounds=bounds,
        backend_name=args.backend,
        count=args.sweep_times,
        between=BUSINESS_WAITS["legion_sweep_between"],
        reward_actions=frozenset({"confirm"}),
        steps=(
            ("sweep", "legion reward claims sweep {index}/{count}: clicked sweep via {backend}", BUSINESS_WAITS["legion_sweep"]),
            ("confirm", "legion reward claims sweep {index}/{count}: clicked confirm via {backend}", BUSINESS_WAITS["legion_sweep_confirm"]),
            ("dismiss", "legion reward claims sweep {index}/{count}: clicked reward-dismiss via {backend}", 0),
        ),
        click_fn=perform_click,
        reward_click_fn=perform_reward_click,
        dismiss_click_fn=perform_dismiss_click,
        sleep_fn=sleep_between,
    )
    for action, message, wait in (
        ("legion_reward_left", "clicked rewards tab", BUSINESS_WAITS["legion_reward_left"]),
        ("legion_reward_claim_top", "clicked legion all-rewards claim", 0),
        ("reward_dismiss", "dismissed legion reward", 0),
        ("legion_personal_reward_tab", "clicked personal rewards tab", 0),
        ("legion_personal_reward_claim_top", "clicked personal all-rewards claim", 0),
        ("reward_dismiss", "dismissed personal reward", 0),
        ("legion_reward_panel_close", "closed rewards panel", 0),
        ("legion_foreign_challenge_back", "returned to legion", 0),
    ):
        click = (
            perform_dismiss_click
            if action == "reward_dismiss"
            else perform_reward_click
            if action in {"legion_reward_claim_top", "legion_personal_reward_claim_top"}
            else perform_click
        )
        backend = click(*points[action], args.backend, bounds)
        if action == "legion_reward_left":
            set_phase_state(args, "legion_rewards_opened")
        print(f"legion reward claims: {message} via {backend}", flush=True)
        if wait:
            sleep_between(wait)
    print(f"legion reward claims complete: attempted full foreign-challenge route via {backend}")
    return 0

def command_legion_sweep_batch(args: argparse.Namespace) -> int:
    if args.times < 1:
        raise ClickError("--times must be >= 1")
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "legion_sweep",
        "legion_sweep_confirm",
        "legion_reward_popup_dismiss",
    )
    points = {
        "sweep": points["legion_sweep"],
        "confirm": points["legion_sweep_confirm"],
        "dismiss": points["legion_reward_popup_dismiss"],
    }
    if args.dry_run:
        print(
            "legion sweep batch dry-run: "
            f"times={args.times}, event_waits={BUSINESS_WAITS}, points={points}"
        )
        return 0
    backend = run_repeated_click_flow(
        points=points,
        bounds=bounds,
        backend_name=args.backend,
        count=args.times,
        between=BUSINESS_WAITS["legion_sweep_between"],
        reward_actions=frozenset({"confirm"}),
        steps=(
            ("sweep", "legion sweep {index}/{count}: clicked sweep via {backend}", BUSINESS_WAITS["legion_sweep"]),
            ("confirm", "legion sweep {index}/{count}: clicked confirm via {backend}", BUSINESS_WAITS["legion_sweep_confirm"]),
            ("dismiss", "legion sweep {index}/{count}: clicked reward-dismiss via {backend}", 0),
        ),
    )
    print(f"legion sweep batch complete: attempted {args.times} via {backend}")
    return 0
