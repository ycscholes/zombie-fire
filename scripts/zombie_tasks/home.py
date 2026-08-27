"""Home tab workflows: mail, calendar, and welfare."""

from __future__ import annotations

from ..zombie_common import *
from ..zombie_actions import *

def command_mail_claim(args: argparse.Namespace) -> int:
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "right_menu",
        "mail_entry",
        "mail_claim_all",
        "mail_reward_popup_dismiss",
        "mail_close",
        "mail_menu_dismiss",
    )
    if args.dry_run:
        print(
            "mail claim dry-run: "
            f"menu_wait={args.menu_wait}, open_wait={args.open_wait}, "
            f"reward_wait={args.reward_wait}, points={points}"
        )
        return 0
    backend = perform_click(*points["right_menu"], args.backend, bounds)
    set_phase_state(args, "mail_menu_opened")
    print(f"mail claim: clicked top-right menu via {backend}", flush=True)
    sleep_between(args.menu_wait)
    backend = perform_click(*points["mail_entry"], args.backend, bounds)
    set_phase_state(args, "mail_opened")
    print(f"mail claim: clicked mail entry via {backend}", flush=True)
    sleep_between(args.open_wait)
    backend = perform_click(*points["mail_claim_all"], args.backend, bounds)
    print(f"mail claim: clicked one-click claim via {backend}", flush=True)
    sleep_between(args.reward_wait)
    backend = perform_dismiss_click(*points["mail_reward_popup_dismiss"], args.backend, bounds)
    print(f"mail claim: clicked reward-dismiss via {backend}", flush=True)
    backend = perform_click(*points["mail_close"], args.backend, bounds)
    print(f"mail claim: clicked close via {backend}", flush=True)
    sleep_between(args.menu_wait)
    backend = perform_click(*points["mail_menu_dismiss"], args.backend, bounds)
    print(f"mail claim complete: dismissed menu via {backend}")
    return 0
def command_calendar_claim(args: argparse.Namespace) -> int:
    """Claim the calendar's visible free gift and return to the home page."""
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "calendar_top",
        "calendar_gift",
        "reward_dismiss",
        "calendar_close",
    )
    if args.dry_run:
        print(
            "calendar claim dry-run: "
            f"open_wait={args.open_wait}, reward_wait={args.reward_wait}, points={points}"
        )
        return 0

    backend = perform_click(*points["calendar_top"], args.backend, bounds)
    set_phase_state(args, "calendar_opened")
    print(f"calendar claim: opened calendar via {backend}", flush=True)
    sleep_between(args.open_wait)
    backend = perform_click(*points["calendar_gift"], args.backend, bounds)
    print(f"calendar claim: clicked visible free gift via {backend}", flush=True)
    sleep_between(args.reward_wait)
    backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
    print(f"calendar claim: dismissed reward via {backend}", flush=True)
    backend = perform_click(*points["calendar_close"], args.backend, bounds)
    print(f"calendar claim complete: closed calendar via {backend}")
    return 0

def command_welfare_claim(args: argparse.Namespace) -> int:
    """Claim the automatic free welfare popup and return without visiting recharge tabs."""
    bounds = prepare_command_bounds(args)
    points = scaled_points(bounds, "welfare_cluster", "welfare_reward_popup_dismiss", "back_bottom_left")
    if args.dry_run:
        print(
            "welfare claim dry-run: "
            f"open_wait={args.open_wait}, reward_wait={args.reward_wait}, points={points}"
        )
        return 0

    backend = perform_click(*points["welfare_cluster"], args.backend, bounds)
    set_phase_state(args, "welfare_opened")
    print(f"welfare claim: opened welfare cluster via {backend}", flush=True)
    sleep_between(args.open_wait)
    backend = perform_dismiss_click(*points["welfare_reward_popup_dismiss"], args.backend, bounds)
    print(f"welfare claim: dismissed automatic free reward via {backend}", flush=True)
    sleep_between(args.reward_wait)
    backend = perform_click(*points["back_bottom_left"], args.backend, bounds)
    print(f"welfare claim complete: returned without visiting recharge tabs via {backend}")
    return 0
