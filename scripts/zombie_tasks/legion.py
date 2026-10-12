"""军团挑战、奖励领取、商店与征途任务。"""

from __future__ import annotations

from ..zombie_common import *
from ..zombie_actions import *
from .resume import LOCAL_TASK_IDS, print_task_selection, select_task_suffix

from .base import scroll_to_bottom as _base_scroll_to_bottom

BUSINESS_WAITS = {
    "legion_foreign_challenge": 0.3,
    "legion_sweep": 0.3,
    "legion_sweep_confirm": 0.3,
    "legion_sweep_between": 0.3,
    "legion_reward_left": 0.3,
}


def scroll_legion_shop_to_bottom(args: argparse.Namespace) -> None:
    """军团商店：使用已校准的拖动坐标将商品列表滚动到底部。"""
    _base_scroll_to_bottom(args, "legion_shop_drag_start", "legion_shop_drag_end")


def _purchase_legion_shop_item(args: argparse.Namespace, points: dict[str, tuple[int, int]], item_action: str, bounds: Bounds) -> None:
    """军团商品购买：选择最大数量，购买并关闭奖励和商品弹窗。"""
    backend = perform_click(*points[item_action], args.backend, bounds)
    print(f"legion shop purchases: opened {item_action} via {backend}", flush=True)
    perform_click(*points["legion_shop_max"], args.backend, bounds)
    perform_reward_click(*points["legion_shop_buy"], args.backend, bounds)
    perform_dismiss_click(*points["legion_shop_reward_dismiss"], args.backend, bounds)
    perform_click(*points["legion_shop_modal_close"], args.backend, bounds)
    print(f"legion shop purchases: completed {item_action}", flush=True)


def command_legion_shop_purchases(args: argparse.Namespace) -> int:
    """军团商店：滚动到底部，依次购买枪械图纸、基建粉末和强化剂后关闭商店。"""
    selection = select_task_suffix(
        LOCAL_TASK_IDS["legion-shop-purchases"],
        getattr(args, "from_task", None),
        "legion-shop-purchases",
    )
    print_task_selection("legion-shop-purchases", selection, dry_run=args.dry_run)
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
        print(f"legion shop purchases dry-run: tasks={selection.remaining}, skipped={selection.skipped}, points={points}")
        return 0

    if getattr(args, "from_task", None) is None:
        backend = perform_click(*points["legion_shop"], args.backend, bounds)
        print(f"legion shop purchases: opened shop via {backend}", flush=True)
        scroll_legion_shop_to_bottom(args)
        print("legion shop purchases: scrolled to bottom via cgclick", flush=True)
    task_actions = {
        "gun_blueprint": "legion_shop_gun_blueprint",
        "base_powder": "legion_shop_base_powder",
        "enhancer": "legion_shop_enhancer",
    }
    for task_id in selection.remaining:
        _purchase_legion_shop_item(args, points, task_actions[task_id], bounds)
    perform_click(*points["legion_shop_close"], args.backend, bounds)
    print(f"legion shop purchases complete: attempted {selection.remaining} and closed shop", flush=True)
    return 0

JOURNEY_GIFT_ACTIONS = (
    "legion_journey_entry", "legion_journey_gifts", "legion_journey_claim_first",
    "legion_journey_reward_dismiss", "legion_journey_go", "legion_journey_sweep_tab",
    "legion_journey_sweep", "legion_journey_search_close",
    "legion_journey_base_entry", "legion_tab",
)
JOURNEY_GIFT_WAITS = {
    "legion_journey_entry": 0.5,
    "legion_journey_gifts": 0.5,
    "legion_journey_base_entry": 1.0,
}


def command_legion_journey_gifts(args: argparse.Namespace) -> int:
    """军团征途：领取首个赠礼并尝试三次搜索扫荡，经地图基地返回军团页。"""
    selection = select_task_suffix(
        LOCAL_TASK_IDS["legion-journey-gifts"],
        getattr(args, "from_task", None),
        "legion-journey-gifts",
    )
    print_task_selection("legion-journey-gifts", selection, dry_run=args.dry_run)
    bounds = prepare_command_bounds(args)
    points = scaled_points(bounds, *JOURNEY_GIFT_ACTIONS)
    steps = []
    if "gift_claim" in selection.remaining:
        steps.extend((
            "legion_journey_entry", "legion_journey_gifts", "legion_journey_claim_first",
            "legion_journey_reward_dismiss",
        ))
    if "expedition" in selection.remaining:
        # 暂时停用“前往”点击，保留坐标以便后续恢复校准。
        # steps.append("legion_journey_go")
        pass  # 扫荡暂时停用，保留有效的空分支。
        # steps.append("legion_journey_sweep_tab")
        # steps.extend(["legion_journey_sweep", "legion_journey_reward_dismiss"] * 3)
        # steps.extend(("legion_journey_search_close", "legion_journey_base_entry", "legion_tab"))
    if args.dry_run:
        print(
            f"legion journey gifts dry-run: tasks={selection.remaining}, skipped={selection.skipped}, "
            f"steps={steps}, event_waits={JOURNEY_GIFT_WAITS}, points={points}"
        )
        return 0
    for action in steps:
        click = (perform_tab_click if action == "legion_tab"
                 else perform_dismiss_click if action == "legion_journey_reward_dismiss"
                 else perform_reward_click if action in {"legion_journey_claim_first", "legion_journey_sweep"}
                 else perform_click)
        backend = click(*points[action], args.backend, bounds)
        if action == "legion_journey_sweep_tab":
            set_phase_state(args, "legion_journey_search_opened")
        elif action == "legion_journey_search_close":
            set_phase_state(args, "legion_journey_search_closed")
        elif action == "legion_journey_base_entry":
            set_phase_state(args, "legion_journey_base_opened")
        elif action == "legion_tab":
            set_phase_state(args, "legion_journey_complete")
        print(f"legion journey gifts: {action} via {backend}", flush=True)
        if action in JOURNEY_GIFT_WAITS:
            sleep_between(JOURNEY_GIFT_WAITS[action])
    print(
        f"legion journey gifts complete: attempted {selection.remaining}; "
        "clicked map base then returned to legion tab",
        flush=True,
    )
    return 0


def _run_legion_daily_cut(args: argparse.Namespace) -> int:
    """每日一刀子任务：进入军团，领取奖励并关闭弹窗，供每日组合任务调用。"""
    bounds = prepare_command_bounds(args)
    actions = ("legion_tab", "legion_daily_cut", "legion_cut_once", "reward_dismiss", "legion_modal_close")
    points = scaled_points(bounds, *actions)
    if args.dry_run:
        print(f"legion daily cut dry-run: points={points}")
        return 0
    for action in actions:
        click = (perform_tab_click if action == "legion_tab"
                 else perform_reward_click if action == "legion_cut_once"
                 else perform_dismiss_click if action == "reward_dismiss"
                 else perform_click)
        backend = click(*points[action], args.backend, bounds)
        if action == "legion_tab":
            set_phase_state(args, "legion_opened")
        elif action == "legion_daily_cut":
            set_phase_state(args, "legion_daily_cut_opened")
        print(f"legion daily cut: {action} via {backend}", flush=True)
    return 0


def command_legion_daily_rewards(args: argparse.Namespace) -> int:
    """军团每日任务：依次执行每日一刀、异域挑战领奖、商店购买和征途赠礼。"""
    selection = select_task_suffix(
        LOCAL_TASK_IDS["legion-daily-rewards"],
        getattr(args, "from_task", None),
        "legion-daily-rewards",
    )
    print_task_selection("legion-daily-rewards", selection, dry_run=args.dry_run)
    if "foreign_rewards" in selection.remaining and args.sweep_times < 1:
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
            f"tasks={selection.remaining}, skipped={selection.skipped}, "
            f"sweep_times={args.sweep_times}, event_waits={BUSINESS_WAITS}, points={points}"
        )

    # 子任务顺序同时用于真实执行和预演；征途赠礼必须最后执行。
    handlers = {
        "daily_cut": _run_legion_daily_cut,
        "foreign_rewards": command_legion_reward_claims,
        "shop": command_legion_shop_purchases,
        "journey_gifts": command_legion_journey_gifts,
    }
    for task_id in selection.remaining:
        child_args = argparse.Namespace(**vars(args))
        child_args.mock_bounds = bounds
        child_args.fit = False
        child_args.from_task = None
        handlers[task_id](child_args)
    if args.dry_run:
        return 0
    print(f"legion daily rewards complete: attempted {selection.remaining}")
    return 0
def command_legion_reward_claims(args: argparse.Namespace) -> int:
    """军团领奖：按指定次数扫荡异域挑战，再领取军团和个人奖励。"""
    selection = select_task_suffix(
        LOCAL_TASK_IDS["legion-reward-claims"],
        getattr(args, "from_task", None),
        "legion-reward-claims",
    )
    print_task_selection("legion-reward-claims", selection, dry_run=args.dry_run)
    if "sweeps" in selection.remaining and args.sweep_times < 1:
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
            f"tasks={selection.remaining}, skipped={selection.skipped}, "
            f"sweep_times={args.sweep_times}, event_waits={BUSINESS_WAITS}, points={points}"
        )
        return 0
    if "sweeps" in selection.remaining:
        backend = perform_tab_click(*points["legion_tab"], args.backend, bounds)
        set_phase_state(args, "legion_opened")
        print(f"legion reward claims: clicked legion tab via {backend}", flush=True)
        backend = perform_action("legion_foreign_challenge", *points["legion_foreign_challenge"], args.backend, bounds, BUSINESS_WAITS)
        set_phase_state(args, "legion_foreign_challenge_opened")
        print(f"legion reward claims: clicked foreign challenge via {backend}", flush=True)
        sweep_args = argparse.Namespace(**vars(args))
        sweep_args.mock_bounds = bounds
        sweep_args.fit = False
        sweep_args.from_task = None
        sweep_args.times = args.sweep_times
        command_legion_sweep_batch(sweep_args)
    elif "legion_rewards" in selection.remaining:
        set_phase_state(args, "legion_foreign_challenge_opened")
    else:
        set_phase_state(args, "legion_rewards_opened")

    reward_tasks = []
    if "legion_rewards" in selection.remaining:
        reward_tasks.extend((
            ("legion_reward_left", "clicked rewards tab", BUSINESS_WAITS["legion_reward_left"]),
            ("legion_reward_claim_top", "clicked legion all-rewards claim", 0),
            ("reward_dismiss", "dismissed legion reward", 0),
        ))
    if "personal_rewards" in selection.remaining:
        reward_tasks.extend((
            ("legion_personal_reward_tab", "clicked personal rewards tab", 0),
            ("legion_personal_reward_claim_top", "clicked personal all-rewards claim", 0),
            ("reward_dismiss", "dismissed personal reward", 0),
        ))
    reward_tasks.extend((
        ("legion_reward_panel_close", "closed rewards panel", 0),
        ("legion_foreign_challenge_back", "returned to legion", 0),
    ))
    for action, message, wait in reward_tasks:
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
    print(f"legion reward claims complete: attempted {selection.remaining} via {backend}")
    return 0

def command_legion_sweep_batch(args: argparse.Namespace) -> int:
    """军团批量扫荡：从已打开的挑战页重复扫荡、确认并关闭奖励弹窗。"""
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
        click_fn=perform_click,
        reward_click_fn=perform_reward_click,
        dismiss_click_fn=perform_dismiss_click,
        sleep_fn=sleep_between,
    )
    print(f"legion sweep batch complete: attempted {args.times} via {backend}")
    return 0
