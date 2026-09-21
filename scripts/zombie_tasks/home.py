"""Home tab workflows: mail, calendar, and welfare."""

from __future__ import annotations

from ..zombie_common import *
from ..zombie_actions import *

BUSINESS_WAITS = {
    "right_menu": 0.3,
    "mail_entry": 0.3,
    "mail_close": 0.3,
    "calendar_top": 0.3,
    "welfare_menu_drag": 0.3,
    "welfare_entry": 0.3,
    "welfare_reward_popup_dismiss": 0.3,
}

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
            f"event_waits={BUSINESS_WAITS}, points={points}"
        )
        return 0
    backend = perform_action("right_menu", *points["right_menu"], args.backend, bounds, BUSINESS_WAITS)
    set_phase_state(args, "mail_menu_opened")
    print(f"mail claim: clicked top-right menu via {backend}", flush=True)
    backend = perform_action("mail_entry", *points["mail_entry"], args.backend, bounds, BUSINESS_WAITS)
    set_phase_state(args, "mail_opened")
    print(f"mail claim: clicked mail entry via {backend}", flush=True)
    backend = perform_action("mail_claim_all", *points["mail_claim_all"], args.backend, bounds, BUSINESS_WAITS)
    print(f"mail claim: clicked one-click claim via {backend}", flush=True)
    backend = perform_action("mail_reward_popup_dismiss", *points["mail_reward_popup_dismiss"], args.backend, bounds, BUSINESS_WAITS, kind="dismiss")
    print(f"mail claim: clicked reward-dismiss via {backend}", flush=True)
    backend = perform_action("mail_close", *points["mail_close"], args.backend, bounds, BUSINESS_WAITS)
    print(f"mail claim: clicked close via {backend}", flush=True)
    backend = perform_action("mail_menu_dismiss", *points["mail_menu_dismiss"], args.backend, bounds, BUSINESS_WAITS, kind="dismiss")
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
            f"event_waits={BUSINESS_WAITS}, points={points}"
        )
        return 0

    backend = perform_action("calendar_top", *points["calendar_top"], args.backend, bounds, BUSINESS_WAITS)
    set_phase_state(args, "calendar_opened")
    print(f"calendar claim: opened calendar via {backend}", flush=True)
    backend = perform_action("calendar_gift", *points["calendar_gift"], args.backend, bounds, BUSINESS_WAITS)
    print(f"calendar claim: clicked visible free gift via {backend}", flush=True)
    backend = perform_action("reward_dismiss", *points["reward_dismiss"], args.backend, bounds, BUSINESS_WAITS, kind="dismiss")
    print(f"calendar claim: dismissed reward via {backend}", flush=True)
    backend = perform_action("calendar_close", *points["calendar_close"], args.backend, bounds, BUSINESS_WAITS)
    print(f"calendar claim complete: closed calendar via {backend}")
    return 0

def command_welfare_claim(args: argparse.Namespace) -> int:
    """Claim the automatic free welfare popup and return without visiting recharge tabs."""
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "welfare_menu_drag_start",
        "welfare_menu_drag_end",
        "welfare_entry",
        "welfare_reward_popup_dismiss",
        "back_bottom_left",
    )
    if args.dry_run:
        print(
            "welfare claim dry-run: "
            f"event_waits={BUSINESS_WAITS}, points={points}"
        )
        return 0

    perform_drag(
        *points["welfare_menu_drag_start"],
        *points["welfare_menu_drag_end"],
        bounds,
    )
    backend = perform_action(
        "welfare_entry",
        *points["welfare_entry"],
        args.backend,
        bounds,
        BUSINESS_WAITS,
        pre_wait_seconds=BUSINESS_WAITS["welfare_menu_drag"],
    )
    set_phase_state(args, "welfare_opened")
    print(f"welfare claim: dragged right-side menu and opened welfare via {backend}", flush=True)
    backend = perform_action(
        "welfare_reward_popup_dismiss",
        *points["welfare_reward_popup_dismiss"],
        args.backend,
        bounds,
        BUSINESS_WAITS,
        kind="dismiss",
    )
    print(f"welfare claim: dismissed automatic free reward via {backend}", flush=True)
    backend = perform_action("back_bottom_left", *points["back_bottom_left"], args.backend, bounds, BUSINESS_WAITS)
    print(f"welfare claim complete: returned without visiting recharge tabs via {backend}")
    return 0
