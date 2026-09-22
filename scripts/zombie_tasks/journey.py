"""Journey tab resource workflow."""

from __future__ import annotations

from ..zombie_common import *
from ..zombie_actions import *


BUSINESS_WAITS = {
    "journey_tab": 1.0,
}

PURIFIER_CLAIM_NAMES = tuple(f"journey_purifier_claim_{index}" for index in range(1, 7))


def command_journey_resource_claim(args: argparse.Namespace) -> int:
    """Open Journey and collect the verified gold and wood resource bubbles once each."""
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
    """Recruit free Journey purifiers and claim their six visible rewards."""
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "journey_tab",
        "journey_purifier_entry",
        "journey_purifier_recruit",
        "journey_purifier_drag_start",
        "journey_purifier_drag_end",
        *PURIFIER_CLAIM_NAMES,
        "reward_dismiss",
    )
    if args.dry_run:
        print(f"journey purifier recruit dry-run: points={points}")
        return 0

    for action in ("journey_tab", "journey_purifier_entry", "journey_purifier_recruit"):
        backend = perform_action(action, *points[action], args.backend, bounds, BUSINESS_WAITS)
        print(f"journey purifier recruit: {action} via {backend}", flush=True)
    set_phase_state(args, "journey_purifier_opened")
    perform_drag(
        *points["journey_purifier_drag_start"],
        *points["journey_purifier_drag_end"],
        bounds,
    )
    for index, action in enumerate(PURIFIER_CLAIM_NAMES, start=1):
        backend = perform_reward_click(*points[action], args.backend, bounds)
        print(f"journey purifier recruit: claimed {index}/6 via {backend}", flush=True)
        backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
        print(f"journey purifier recruit: dismissed reward {index}/6 via {backend}", flush=True)
    return 0


def command_journey_daily_rewards(args: argparse.Namespace) -> int:
    """Run the existing Journey resources followed by the purifier route."""
    command_journey_resource_claim(args)
    return command_journey_purifier_recruit(args)
