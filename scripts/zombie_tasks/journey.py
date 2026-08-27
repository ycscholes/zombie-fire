"""Journey tab resource workflow."""

from __future__ import annotations

from ..zombie_common import *
from ..zombie_actions import *

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

    backend = perform_click(*points["journey_tab"], args.backend, bounds)
    print(f"journey resource claim: opened journey tab via {backend}", flush=True)
    backend = perform_click(*points["journey_gold_claim"], args.backend, bounds)
    print(f"journey resource claim: collected gold resource via {backend}", flush=True)
    backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
    print(f"journey resource claim: dismissed gold reward popup via {backend}", flush=True)
    backend = perform_click(*points["journey_wood_claim"], args.backend, bounds)
    print(f"journey resource claim: collected wood resource via {backend}", flush=True)
    backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
    print(f"journey resource claim: dismissed wood reward popup via {backend}")
    return 0
