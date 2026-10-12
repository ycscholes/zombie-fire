"""每日任务八阶段编排、进度记录与失败恢复。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from ..zombie_common import *
from ..zombie_actions import *
from .patrol import command_patrol_full_from_home
from .home import command_calendar_claim, command_welfare_claim, command_mail_claim
from .legion import command_legion_daily_rewards
from .journey import command_journey_daily_rewards
from .base import command_base_training_hall
from .shop import command_shop_training_hall
from .resume import DAILY_TASK_IDS, DAILY_TASK_TARGETS, print_task_selection, select_task_suffix

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
    """阶段恢复：根据已记录的页面状态，尝试退出失败阶段到已知安全位置。"""
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
        "legion_journey_complete": (),
        "legion_journey_search_opened": ("legion_journey_search_close",),
        "legion_journey_search_closed": ("legion_journey_base_entry",),
        "legion_journey_base_opened": ("legion_tab",),
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
    """执行单个每日阶段，记录进度并在点击投递失败时尝试恢复。"""
    progress = PhaseProgress(name)
    args.phase_progress = progress
    try:
        handler(args)
        return PhaseResult(name, "completed")
    except ClickDeliveryError as exc:
        recover_phase(progress, args)
        return PhaseResult(name, "recovered_failure", str(exc))


def print_daily_summary(results: list[PhaseResult], task_selection=None) -> None:
    """输出每日任务各阶段的完成、跳过或失败结果。"""
    status = "partial" if any(result.status == "recovered_failure" for result in results) else "complete"
    rendered = ", ".join(
        f"{result.name}={result.status}" + (f" ({result.error})" if result.error else "")
        for result in results
    )
    task_summary = ""
    if task_selection is not None:
        skipped = ", ".join(task_selection.skipped) or "none"
        task_summary = (
            f"; from_task={task_selection.selected}, "
            f"skipped_tasks=[{skipped}], remaining_tasks=[{', '.join(task_selection.remaining)}]"
        )
    print(f"daily rewards {status}: {rendered}{task_summary}")


def command_daily_rewards(args: argparse.Namespace) -> int:
    """每日奖励总任务：在同一游戏窗口内依次执行八个阶段，支持从指定阶段继续。"""
    from_task = getattr(args, "from_task", None)
    task_selection = select_task_suffix(DAILY_TASK_IDS, from_task, "daily-rewards")
    if from_task is not None:
        print_task_selection("daily-rewards", task_selection, dry_run=args.dry_run)
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
        bind_input_session(bounds)

    phase_values = {
        **vars(args),
        "mock_bounds": bounds,
        "fit": False,
        "quick_times": 3,
        "ad_times": 5,
        "panel_wait": 0.3,
        "claim_wait": 1,
        "dismiss_wait": 0.3,
        "quick_reward_wait": 0.3,
        "quick_between": 0.3,
        "ad_wait": 33.0,
        "ad_close_wait": 0.5,
        "ad_reward_wait": 1.0,
        "ad_between": 0.5,
        "close_wait": 0.3,
        "menu_wait": 0.3,
        "open_wait": 0.3,
        "reward_wait": 0.3,
        "sweep_times": 2,
        "confirm_wait": 0.3,
        "sweep_reward_wait": 0.3,
        "sweep_between": 0.3,
        "reward_page_wait": 0.3,
        "battle_times": 5,
        "skip_scroll": False,
        "from_task": None,
    }
    phase_args = argparse.Namespace(**phase_values)

    phases: tuple[tuple[str, Callable[[argparse.Namespace], int]], ...] = (
        ("patrol", command_patrol_full_from_home),
        ("calendar", command_calendar_claim),
        ("welfare", command_welfare_claim),
        ("mail", command_mail_claim),
        ("legion", command_legion_daily_rewards),
        ("journey", command_journey_daily_rewards),
        ("base", command_base_training_hall),
        ("shop", command_shop_training_hall),
    )
    selected_phase = None
    selected_local_task = None
    if from_task is not None:
        selected_phase, selected_local_task = DAILY_TASK_TARGETS[from_task]
        start_index = next(index for index, (name, _) in enumerate(phases) if name == selected_phase)
    else:
        from_step = getattr(args, "from_step", 1)
        start_index = from_step - 1
    results: list[PhaseResult] = [
        PhaseResult(name, "skipped") for name, _ in phases[:start_index]
    ]
    for index, (name, handler) in enumerate(phases[start_index:], start=start_index):
        phase_args.from_task = selected_local_task if name == selected_phase else None
        suffix = f" from task {phase_args.from_task}" if phase_args.from_task else ""
        print(f"daily rewards: starting step {index + 1} {name}{suffix}", flush=True)
        try:
            results.append(run_daily_phase(name, handler, phase_args))
        except ClickError as exc:
            results.append(PhaseResult(name, "fatal_failure", str(exc)))
            results.extend(PhaseResult(skipped_name, "skipped") for skipped_name, _ in phases[index + 1 :])
            print_daily_summary(results, task_selection if from_task is not None else None)
            raise
    print_daily_summary(results, task_selection if from_task is not None else None)
    return 0
