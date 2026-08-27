"""Eight-phase daily orchestration and recovery."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from ..zombie_common import *
from ..zombie_actions import *
from .patrol import command_patrol_full_from_home
from .home import command_calendar_claim, command_welfare_claim, command_mail_claim
from .legion import command_legion_daily_rewards
from .journey import command_journey_resource_claim
from .base import command_base_training_hall
from .shop import command_shop_training_hall

@dataclass
class PhaseProgress:
    name: str
    state: str = "not_entered"


@dataclass(frozen=True)
class PhaseResult:
    name: str
    status: str
    error: str | None = None


def recover_phase(progress: PhaseProgress, args: argparse.Namespace) -> None:
    """Return a failed composite phase to its known safe boundary when possible."""
    if progress.state == "not_entered" or args.dry_run:
        return
    bounds = args.mock_bounds
    actions_by_state = {
        "patrol_opened": ("patrol_close",),
        "calendar_opened": ("calendar_close",),
        "welfare_opened": ("back_bottom_left",),
        "mail_menu_opened": ("mail_menu_dismiss",),
        "mail_opened": ("mail_close", "mail_menu_dismiss"),
        "legion_opened": (),
        "legion_daily_cut_opened": ("legion_modal_close",),
        "legion_foreign_challenge_opened": ("legion_foreign_challenge_back",),
        "legion_rewards_opened": ("legion_reward_panel_close", "legion_foreign_challenge_back"),
    }
    try:
        actions = actions_by_state.get(progress.state)
        if actions is None:
            raise PhaseRecoveryError(f"{progress.name} has no safe recovery from {progress.state}")
        ensure_unchanged_game_window(bounds)
        for action in actions:
            x, y = scale_point(ACTIONS[action], bounds)
            perform_click(x, y, args.backend, bounds)
    except ClickError as exc:
        raise PhaseRecoveryError(f"{progress.name} recovery failed from {progress.state}: {exc}") from exc


def run_daily_phase(
    name: str,
    handler: Callable[[argparse.Namespace], int],
    args: argparse.Namespace,
) -> PhaseResult:
    progress = PhaseProgress(name)
    args.phase_progress = progress
    try:
        handler(args)
        return PhaseResult(name, "completed")
    except ClickDeliveryError as exc:
        recover_phase(progress, args)
        return PhaseResult(name, "recovered_failure", str(exc))


def print_daily_summary(results: list[PhaseResult]) -> None:
    status = "partial" if any(result.status == "recovered_failure" for result in results) else "complete"
    rendered = ", ".join(
        f"{result.name}={result.status}" + (f" ({result.error})" if result.error else "")
        for result in results
    )
    print(f"daily rewards {status}: {rendered}")


def command_daily_rewards(args: argparse.Namespace) -> int:
    """Run all eight configured daily-reward phases against one checked window."""
    if args.mock_bounds:
        bounds = get_bounds(args)
        validate_bounds(bounds, allow_mock=True)
    else:
        snapshot = front_window_snapshot()
        status = classify_snapshot(snapshot)
        if status != "game_ready":
            raise WindowStateError(
                "game window is not ready: "
                f"{status} title={snapshot.get('title')!r} "
                f"app={snapshot.get('app')!r} bundle={snapshot.get('bundle')!r}"
            )
        bounds = fit_game_window() if args.fit else ensure_valid_game_bounds(get_bounds(args))
        validate_bounds(bounds, allow_mock=False)

    phase_values = {
        **vars(args),
        "mock_bounds": bounds,
        "fit": False,
        "quick_times": 3,
        "ad_times": 5,
        "panel_wait": 2.0,
        "claim_wait": 2.0,
        "dismiss_wait": 1.0,
        "quick_reward_wait": 4.5,
        "quick_between": 2.0,
        "ad_wait": 33.0,
        "ad_close_wait": 1.2,
        "ad_reward_wait": 1.0,
        "ad_between": 2.0,
        "close_wait": 1.5,
        "menu_wait": 1.0,
        "open_wait": 1.0,
        "reward_wait": 1.2,
        "sweep_times": 2,
        "confirm_wait": 0.8,
        "sweep_reward_wait": 1.2,
        "sweep_between": 0.6,
        "reward_page_wait": 4.0,
        "battle_times": 5,
        "skip_scroll": False,
    }
    phase_args = argparse.Namespace(**phase_values)

    phases: tuple[tuple[str, Callable[[argparse.Namespace], int]], ...] = (
        ("patrol", command_patrol_full_from_home),
        ("calendar", command_calendar_claim),
        ("welfare", command_welfare_claim),
        ("mail", command_mail_claim),
        ("legion", command_legion_daily_rewards),
        ("journey", command_journey_resource_claim),
        ("base", command_base_training_hall),
        ("shop", command_shop_training_hall),
    )
    from_step = getattr(args, "from_step", 1)
    start_index = from_step - 1
    results: list[PhaseResult] = [
        PhaseResult(name, "skipped") for name, _ in phases[:start_index]
    ]
    for index, (name, handler) in enumerate(phases[start_index:], start=start_index):
        print(f"daily rewards: starting step {index + 1} {name}", flush=True)
        try:
            results.append(run_daily_phase(name, handler, phase_args))
        except ClickError as exc:
            results.append(PhaseResult(name, "fatal_failure", str(exc)))
            results.extend(PhaseResult(skipped_name, "skipped") for skipped_name, _ in phases[index + 1 :])
            print_daily_summary(results)
            raise
    print_daily_summary(results)
    return 0
