"""Base tab training-hall workflow."""

from __future__ import annotations

from ..zombie_common import *
from ..zombie_actions import *

BUSINESS_WAITS = {
    "abyss_challenge": 3.0,
    "abyss_entry": 0.5,
    "abyss_fail_return": 2.0,
    "battle_challenge": 1.0,
    "core_trial": 0.5,
    "global_rescue_challenge": 1.5,
    "training_hall": 2.5,
    "terminal_crisis_confirm": 0.5,
}


def _click_action(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    action: str,
    bounds: Bounds,
    *,
    dismiss: bool = False,
    reward: bool = False,
    post_wait_seconds: float | None = None,
) -> str:
    if dismiss:
        backend = perform_dismiss_click(*points[action], args.backend, bounds)
    elif reward:
        backend = perform_reward_click(*points[action], args.backend, bounds)
    elif action in BOTTOM_TAB_ACTION_NAMES:
        backend = perform_tab_click(*points[action], args.backend, bounds)
    elif post_wait_seconds is not None:
        backend = perform_click(*points[action], args.backend, bounds, wait_after=False)
        time.sleep(post_wait_seconds)
    else:
        backend = perform_action(action, *points[action], args.backend, bounds, BUSINESS_WAITS)
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
    x1, y1 = scale_point(ACTIONS[start_action], bounds)
    x2, y2 = scale_point(ACTIONS[end_action], bounds)
    perform_drag(x1, y1, x2, y2, bounds)
    time.sleep(1.0)


def _run_deep_abyss_subtask(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    bounds: Bounds,
) -> None:
    """Fail one Deep Abyss challenge, then attempt two sweeps and return to the hall."""
    _click_action(args, points, "abyss_entry", bounds)
    _click_action(args, points, "abyss_challenge", bounds)
    _click_action(args, points, "reward_dismiss", bounds, post_wait_seconds=0.5)
    _click_action(args, points, "abyss_pause", bounds)
    _click_action(args, points, "abyss_pause_exit", bounds)
    _click_action(args, points, "abyss_fail_return", bounds)

    for index in range(2):
        _click_action(args, points, "abyss_sweep", bounds, reward=True)
        _click_action(args, points, "reward_dismiss", bounds, dismiss=True)
        print(f"base training hall: Deep Abyss sweep {index + 1}/2 attempted", flush=True)

    _click_action(args, points, "abyss_back", bounds)
    # The Deep Abyss back button exits to the main game; return to the hall route.
    _click_action(args, points, "base_tab", bounds)


def command_base_training_hall_deep_abyss(args: argparse.Namespace) -> int:
    """Run the Deep Abyss subtask from the training-hall list page."""
    bounds = prepare_command_bounds(args)
    args.active_bounds = bounds
    names = (
        "abyss_entry", "abyss_challenge",
        "abyss_monster_info_confirm", "abyss_skill_select_confirm", "abyss_pause",
        "abyss_pause_exit", "abyss_fail_return", "abyss_sweep", "reward_dismiss",
        "abyss_back", "base_tab",
    )
    points = scaled_points(bounds, *names)
    if args.dry_run:
        print(f"Deep Abyss subtask dry-run: points={points}")
        return 0

    _run_deep_abyss_subtask(args, points, bounds)
    print("Deep Abyss subtask complete: challenge failed, two sweeps attempted, returned to training hall", flush=True)
    return 0


def _purchase_play_shop_item(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    item_action: str,
    bounds: Bounds,
) -> None:
    backend = perform_click(*points[item_action], args.backend, bounds)
    print(f"base training hall shop: opened {item_action} via {backend}", flush=True)
    perform_click(*points["play_shop_max"], args.backend, bounds)
    perform_reward_click(*points["play_shop_buy"], args.backend, bounds)
    perform_dismiss_click(*points["play_shop_reward_dismiss"], args.backend, bounds)
    perform_click(*points["play_shop_modal_close"], args.backend, bounds)
    print(f"base training hall shop: completed {item_action}", flush=True)


def command_base_training_hall_shop(args: argparse.Namespace) -> int:
    """Run the play-shop purchase route from the already-open training hall."""
    bounds = prepare_command_bounds(args)
    args.active_bounds = bounds
    names = (
        "play_shop", "play_shop_enhancer", "play_shop_battle_tab",
        "play_shop_battle_drag_start", "play_shop_battle_drag_end", "play_shop_gun_blueprint",
        "play_shop_tabs_drag_start", "play_shop_tabs_drag_end", "play_shop_element_tab",
        "play_shop_base_material", "play_shop_legion_tab", "play_shop_skill_manual",
        "play_shop_max", "play_shop_buy", "play_shop_reward_dismiss", "play_shop_modal_close",
        "play_shop_close",
    )
    points = scaled_points(bounds, *names)
    if args.dry_run:
        print(f"base training hall shop dry-run: points={points}")
        return 0

    perform_click(*points["play_shop"], args.backend, bounds)
    _purchase_play_shop_item(args, points, "play_shop_enhancer", bounds)
    perform_click(*points["play_shop_battle_tab"], args.backend, bounds)
    scroll_to_bottom(args, "play_shop_battle_drag_start", "play_shop_battle_drag_end")
    _purchase_play_shop_item(args, points, "play_shop_gun_blueprint", bounds)
    scroll_to_bottom(args, "play_shop_tabs_drag_start", "play_shop_tabs_drag_end")
    perform_click(*points["play_shop_element_tab"], args.backend, bounds)
    _purchase_play_shop_item(args, points, "play_shop_base_material", bounds)
    # 暂时不购买legion_tab和skill_manual
    # perform_click(*points["play_shop_legion_tab"], args.backend, bounds)
    # _purchase_play_shop_item(args, points, "play_shop_skill_manual", bounds)
    sleep_between(0.5)
    perform_click(*points["play_shop_close"], args.backend, bounds)
    print("base training hall shop complete: purchased four items and closed shop", flush=True)
    return 0


def _run_global_rescue_subtask(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    bounds: Bounds,
) -> None:
    _click_action(args, points, "global_rescue_challenge", bounds)
    _click_action(args, points, "global_rescue_free", bounds, reward=True)
    _click_action(args, points, "training_reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "training_hall_back", bounds)


def _run_terminal_crisis_subtask(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    bounds: Bounds,
) -> None:
    scroll_to_bottom(args)
    if not getattr(args, "skip_scroll", False):
        print("base training hall: scroll_to_bottom (scrolled) via cgclick", flush=True)
    _click_action(args, points, "terminal_crisis_challenge", bounds)
    _click_action(args, points, "terminal_crisis_sweep", bounds)
    _click_action(args, points, "terminal_crisis_confirm", bounds, reward=True)
    _click_action(args, points, "training_reward_dismiss", bounds, dismiss=True)
    sleep_between(0.5)
    _click_action(args, points, "training_hall_back", bounds)


def _run_battlefield_contest_subtask(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    bounds: Bounds,
) -> None:
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


def _run_element_trial_subtask(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    bounds: Bounds,
) -> None:
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


def _command_training_hall_subtask(
    args: argparse.Namespace,
    label: str,
    action_names: tuple[str, ...],
    route: Callable[[argparse.Namespace, dict[str, tuple[int, int]], Bounds], None],
    *,
    scroll_hall_to_bottom: bool = False,
) -> int:
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


def command_base_training_hall_global_rescue(args: argparse.Namespace) -> int:
    return _command_training_hall_subtask(
        args,
        "Global Rescue",
        ("global_rescue_challenge", "global_rescue_free", "training_reward_dismiss", "training_hall_back"),
        _run_global_rescue_subtask,
    )


def command_base_training_hall_terminal_crisis(args: argparse.Namespace) -> int:
    return _command_training_hall_subtask(
        args,
        "Terminal Crisis",
        ("terminal_crisis_challenge", "terminal_crisis_sweep", "terminal_crisis_confirm", "training_reward_dismiss", "training_hall_back"),
        _run_terminal_crisis_subtask,
    )


def command_base_training_hall_battlefield_contest(args: argparse.Namespace) -> int:
    if args.battle_times < 1:
        raise ClickError("--battle-times must be >= 1")
    return _command_training_hall_subtask(
        args,
        "Battlefield Contest",
        ("battle_challenge", "battle_castle", "reward_dismiss", "battle_modal_challenge", "battle_sweep_last", "battle_reward_dismiss", "battle_modal_close", "training_hall_back"),
        _run_battlefield_contest_subtask,
        scroll_hall_to_bottom=True,
    )


def command_base_training_hall_element_trial(args: argparse.Namespace) -> int:
    return _command_training_hall_subtask(
        args,
        "Element Trial",
        ("element_challenge", "core_trial", "idle_button", "idle_claim", "reward_dismiss", "idle_cancel", "core_sweep", "core_sweep_ten", "core_sweep_close", "core_trial_back", "element_back"),
        _run_element_trial_subtask,
        scroll_hall_to_bottom=True,
    )


def command_base_training_hall(args: argparse.Namespace) -> int:
    """Run the verified free base, training-hall, battlefield, and element routes."""
    if args.battle_times < 1:
        raise ClickError("--battle-times must be >= 1")
    bounds = prepare_command_bounds(args)
    args.active_bounds = bounds
    names = (
        "base_tab", "cafeteria", "cafeteria_claim", "cafeteria_back", "training_reward_dismiss", "battle_reward_dismiss",
        "training_hall", "global_rescue_challenge", "global_rescue_free", "abyss_entry",
        "abyss_challenge", "abyss_monster_info_confirm",
        "abyss_skill_select_confirm", "abyss_pause", "abyss_pause_exit", "abyss_fail_return",
        "abyss_sweep", "abyss_back", "terminal_crisis_challenge",
        "terminal_crisis_sweep", "terminal_crisis_confirm", "battle_challenge", "battle_castle", "battle_modal_challenge",
        "battle_modal_drag_start", "battle_modal_drag_end", "battle_sweep_last", "reward_dismiss", "battle_modal_close",
        "training_hall_back", "element_challenge", "core_trial", "idle_button",
        "idle_claim", "idle_cancel", "core_sweep", "core_sweep_ten", "core_sweep_close", "core_trial_back",
        "element_back",
    )
    points = scaled_points(bounds, *names)
    if args.dry_run:
        print(f"base training hall dry-run: battle_times={args.battle_times}, skip_scroll={args.skip_scroll}, points={points}")
        return 0

    _click_action(args, points, "base_tab", bounds)
    _click_action(args, points, "cafeteria", bounds)
    _click_action(args, points, "cafeteria_claim", bounds, reward=True)
    _click_action(args, points, "training_reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "cafeteria_back", bounds)
    _click_action(args, points, "training_hall", bounds)
    _run_global_rescue_subtask(args, points, bounds)
    _run_deep_abyss_subtask(args, points, bounds)
    _run_terminal_crisis_subtask(args, points, bounds)
    _run_battlefield_contest_subtask(args, points, bounds)
    _run_element_trial_subtask(args, points, bounds)
    command_base_training_hall_shop(
        argparse.Namespace(mock_bounds=bounds, backend=args.backend, dry_run=False)
    )
    sleep_between(0.5)
    backend = _click_action(args, points, "training_hall_back", bounds)
    print(
        "base training hall complete: claimed cafeteria, Global Rescue, Terminal Crisis, "
        f"attempted battle={args.battle_times} and element trial via {backend}"
    )
    return 0
