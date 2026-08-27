"""Base tab training-hall workflow."""

from __future__ import annotations

from ..zombie_common import *
from ..zombie_actions import *


def _click_action(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    action: str,
    bounds: Bounds,
    *,
    dismiss: bool = False,
) -> str:
    click = perform_dismiss_click if dismiss else perform_click
    backend = click(*points[action], args.backend, bounds)
    verb = "dismissed" if dismiss else "clicked"
    print(f"base training hall: {action} ({verb}) via {backend}", flush=True)
    return backend


def scroll_to_bottom(
    args: argparse.Namespace,
    start_action: str = "training_hall_drag_start",
    end_action: str = "training_hall_drag_end",
) -> None:
    """Scroll a focused base-task list down with CoreGraphics."""
    if getattr(args, "skip_scroll", False):
        return
    bounds = args.active_bounds
    focus_game_window(bounds)
    ensure_unchanged_game_window(bounds)
    x1, y1 = scale_point(ACTIONS[start_action], bounds)
    x2, y2 = scale_point(ACTIONS[end_action], bounds)
    if not drag_cgclick_bin(x1, y1, x2, y2):
        raise ClickDeliveryError("CoreGraphics drag backend unavailable")
    time.sleep(1.0)


def command_base_training_hall(args: argparse.Namespace) -> int:
    """Run the verified free base, training-hall, battlefield, and element routes."""
    if args.battle_times < 1:
        raise ClickError("--battle-times must be >= 1")
    bounds = prepare_command_bounds(args)
    args.active_bounds = bounds
    names = (
        "base_tab", "cafeteria", "cafeteria_claim", "cafeteria_back", "training_reward_dismiss",
        "training_hall", "global_rescue_challenge", "global_rescue_free", "terminal_crisis_challenge",
        "terminal_crisis_sweep", "terminal_crisis_confirm", "battle_challenge", "battle_castle", "battle_modal_challenge",
        "battle_modal_drag_start", "battle_modal_drag_end", "battle_sweep_last", "reward_dismiss", "battle_modal_close",
        "training_hall_back", "element_challenge", "core_trial", "idle_button",
        "idle_claim", "idle_cancel", "core_sweep", "core_sweep_ten", "core_trial_back",
        "element_back",
    )
    points = scaled_points(bounds, *names)
    if args.dry_run:
        print(f"base training hall dry-run: battle_times={args.battle_times}, skip_scroll={args.skip_scroll}, points={points}")
        return 0

    _click_action(args, points, "base_tab", bounds)
    _click_action(args, points, "cafeteria", bounds)
    _click_action(args, points, "cafeteria_claim", bounds)
    _click_action(args, points, "training_reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "cafeteria_back", bounds)
    _click_action(args, points, "training_hall", bounds)
    _click_action(args, points, "global_rescue_challenge", bounds)
    _click_action(args, points, "global_rescue_free", bounds)
    _click_action(args, points, "training_reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "training_hall_back", bounds)
    scroll_to_bottom(args)
    if not args.skip_scroll:
        print("base training hall: scroll_to_bottom (scrolled) via cgclick", flush=True)
    _click_action(args, points, "terminal_crisis_challenge", bounds)
    _click_action(args, points, "terminal_crisis_sweep", bounds)
    _click_action(args, points, "terminal_crisis_confirm", bounds)
    _click_action(args, points, "training_reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "training_hall_back", bounds)
    _click_action(args, points, "battle_challenge", bounds)
    _click_action(args, points, "battle_castle", bounds)
    _click_action(args, points, "reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "battle_modal_challenge", bounds)
    scroll_to_bottom(args, "battle_modal_drag_start", "battle_modal_drag_end")
    if not args.skip_scroll:
        print("base training hall: battle_modal_scroll_to_bottom (scrolled) via cgclick", flush=True)
    for index in range(args.battle_times):
        _click_action(args, points, "battle_sweep_last", bounds)
        _click_action(args, points, "reward_dismiss", bounds, dismiss=True)
        print(f"base training hall: battlefield sweep {index + 1}/{args.battle_times} complete", flush=True)
    _click_action(args, points, "battle_modal_close", bounds)
    _click_action(args, points, "training_hall_back", bounds)
    _click_action(args, points, "element_challenge", bounds)
    _click_action(args, points, "core_trial", bounds)
    _click_action(args, points, "idle_button", bounds)
    _click_action(args, points, "idle_claim", bounds)
    _click_action(args, points, "reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "idle_cancel", bounds)
    _click_action(args, points, "core_sweep", bounds)
    _click_action(args, points, "core_sweep_ten", bounds)
    _click_action(args, points, "reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "core_trial_back", bounds)
    _click_action(args, points, "element_back", bounds)
    backend = _click_action(args, points, "training_hall_back", bounds)
    print(
        "base training hall complete: claimed cafeteria, Global Rescue, Terminal Crisis, "
        f"attempted battle={args.battle_times} and element trial via {backend}"
    )
    return 0
