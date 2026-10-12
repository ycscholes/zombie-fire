"""征途资源领取与净化者招募任务。"""

from __future__ import annotations

from ..zombie_common import *
from ..zombie_actions import *
from .resume import LOCAL_TASK_IDS, print_task_selection, select_task_suffix


BUSINESS_WAITS = {
    "journey_tab": 1.0,
}

def command_journey_resource_claim(args: argparse.Namespace) -> int:
    """征途资源：进入征途，分别领取金币和木材并关闭奖励弹窗。"""
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "journey_tab",
        "journey_gold_claim",
        "journey_wood_claim",
        "reward_dismiss",
    )
    if args.dry_run:
        print(f"journey resource claim dry-run: points={points}")
        return 0

    backend = perform_action(
        "journey_tab",
        *points["journey_tab"],
        args.backend,
        bounds,
        BUSINESS_WAITS,
    )
    print(f"journey resource claim: opened journey tab via {backend}", flush=True)
    backend = perform_reward_click(*points["journey_gold_claim"], args.backend, bounds)
    print(f"journey resource claim: collected gold resource via {backend}", flush=True)
    backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
    print(f"journey resource claim: dismissed gold reward popup via {backend}", flush=True)
    backend = perform_reward_click(*points["journey_wood_claim"], args.backend, bounds)
    print(f"journey resource claim: collected wood resource via {backend}", flush=True)
    backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
    print(f"journey resource claim: dismissed wood reward popup via {backend}")
    return 0


def command_journey_purifier_recruit(args: argparse.Namespace) -> int:
    """净化者招募：进入征途招募页面，执行一键招募并领取奖励。"""
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "journey_tab",
        "journey_purifier_entry",
        "journey_purifier_recruit",
        "journey_purifier_claim",
        "reward_dismiss",
    )
    if args.dry_run:
        print(f"journey purifier recruit dry-run: points={points}")
        return 0

    for action in ("journey_tab", "journey_purifier_entry", "journey_purifier_recruit"):
        backend = perform_action(action, *points[action], args.backend, bounds, BUSINESS_WAITS)
        print(f"journey purifier recruit: {action} via {backend}", flush=True)
    set_phase_state(args, "journey_purifier_opened")
    backend = perform_reward_click(*points["journey_purifier_claim"], args.backend, bounds)
    print(f"journey purifier recruit: claimed via {backend}", flush=True)
    backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
    print(f"journey purifier recruit: dismissed reward via {backend}", flush=True)

    return 0


def command_journey_daily_rewards(args: argparse.Namespace) -> int:
    """征途每日任务：依次领取资源和执行净化者招募。"""
    selection = select_task_suffix(
        LOCAL_TASK_IDS["journey-daily-rewards"],
        getattr(args, "from_task", None),
        "journey-daily-rewards",
    )
    print_task_selection("journey-daily-rewards", selection, dry_run=args.dry_run)
    for task_id, handler in (
        ("resources", command_journey_resource_claim),
        ("purifier", command_journey_purifier_recruit),
    ):
        if task_id in selection.remaining:
            child_args = argparse.Namespace(**vars(args))
            child_args.from_task = None
            handler(child_args)
    return 0
