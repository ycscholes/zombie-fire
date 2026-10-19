"""每日任务十二阶段编排、进度记录与失败恢复。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from ..zombie_common import *
from ..zombie_actions import *
from .patrol import command_patrol_full_from_home
from .mechanical_shock import command_mechanical_shock
from .battle_pass import command_battle_pass_daily
from .armed import command_armed_descent
from .mimic import command_mimic_card_library
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
        "mechanical_shock_entry_in_progress": ("back_bottom_left",),
        "mechanical_shock_page_opened": ("back_bottom_left",),
        "mechanical_shock_animation_in_progress": ("back_bottom_left",),
        "mechanical_shock_tasks_opening": ("mechanical_shock_tasks_close", "back_bottom_left"),
        "mechanical_shock_tasks_opened": ("mechanical_shock_tasks_close", "back_bottom_left"),
        "mechanical_shock_tasks_closing": ("mechanical_shock_tasks_close", "back_bottom_left"),
        "mechanical_shock_task_claim_in_progress": (
            "reward_dismiss", "mechanical_shock_tasks_close", "back_bottom_left",
        ),
        "mechanical_shock_mech_fight_opening": ("back_bottom_left",),
        "mechanical_shock_mech_fight_opened": ("back_bottom_left",),
        "mechanical_shock_mech_fight_claim_in_progress": ("reward_dismiss", "back_bottom_left"),
        "mechanical_shock_home_return_in_progress": ("back_bottom_left",),
        "battle_pass_opened": ("back_bottom_left",),
        "battle_pass_work_plan_opened": ("back_bottom_left",),
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
        "mimic_page_opened": ("back_bottom_left",),
        "mimic_tasks_opened": ("mimic_tasks_close", "back_bottom_left"),
        "mimic_rewards_opened": ("back_bottom_left", "back_bottom_left"),
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
    args.task_skipped_reason = None
    try:
        handler(args)
        skipped_reason = getattr(args, "task_skipped_reason", None)
        if skipped_reason:
            return PhaseResult(name, "skipped", skipped_reason)
        return PhaseResult(name, "completed")
    except ClickDeliveryError as exc:
        recover_phase(progress, args)
        return PhaseResult(name, "recovered_failure", str(exc))


def print_daily_summary(results: list[PhaseResult], task_selection=None) -> None:
    """输出每日任务各阶段的完成、跳过或失败结果。"""
    status = "partial" if any(
        result.status in {"recovered_failure", "fatal_failure"}
        or (result.status == "skipped" and result.error is not None)
        for result in results
    ) else "complete"
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
    """每日奖励总任务：依次执行十二个阶段，保留旧 from-step 编号并支持 named resume。"""
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
        "free_claim_state": getattr(args, "pass_free_claim_state", None),
        "work_plan_sign_state": getattr(args, "pass_work_plan_sign_state", None),
        "skip_animation_state": getattr(args, "armed_skip_animation_state", None),
        "free_draw_state": getattr(args, "armed_free_draw_state", None),
        "task_claims": getattr(args, "armed_task_claims", None),
        "mechanical_shock_skip_animation_state": getattr(args, "mechanical_shock_skip_animation_state", None),
        "mechanical_shock_task_claims": getattr(args, "mechanical_shock_task_claims", None),
        "mechanical_shock_mech_fight_claim_state": getattr(args, "mechanical_shock_mech_fight_claim_state", None),
        "mimic_skip_animation_state": getattr(args, "mimic_skip_animation_state", None),
        "mimic_free_draw_state": getattr(args, "mimic_free_draw_state", None),
        "mimic_task_claims": getattr(args, "mimic_task_claims", None),
        "mimic_one_click_claim_state": getattr(args, "mimic_one_click_claim_state", None),
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

    # 完整流程在巡逻后依次执行机械震荡、通行证、武装降临和拟态牌库；旧 from-step 仍从日历开始。
    phases: tuple[tuple[str, Callable[[argparse.Namespace], int]], ...] = (
        ("patrol", command_patrol_full_from_home),
        ("mechanical_shock", command_mechanical_shock),
        ("battle_pass", command_battle_pass_daily),
        ("armed_descent", command_armed_descent),
        ("mimic_card_library", command_mimic_card_library),
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
        # 旧编号 2-8 继续从日历到商城开始；新增阶段只插入完整流程巡逻之后。
        legacy_phase = ("patrol", "calendar", "welfare", "mail", "legion", "journey", "base", "shop")[from_step - 1]
        start_index = next(index for index, (name, _) in enumerate(phases) if name == legacy_phase)
    results: list[PhaseResult] = [
        PhaseResult(name, "skipped") for name, _ in phases[:start_index]
    ]
    for index, (name, handler) in enumerate(phases[start_index:], start=start_index):
        phase_args.from_task = selected_local_task if name == selected_phase else None
        suffix = f" from task {phase_args.from_task}" if phase_args.from_task else ""
        print(f"daily rewards: starting step {index + 1} {name}{suffix}", flush=True)
        if name == "armed_descent" and not all(
            getattr(phase_args, gate, None) is not None
            for gate in ("skip_animation_state", "free_draw_state", "task_claims")
        ):
            reason = "requires current-run --armed-skip-animation-state, --armed-free-draw-state, and --armed-task-claims gates"
            results.append(PhaseResult(name, "skipped", reason))
            print(f"daily rewards: skipped {name}: {reason}", flush=True)
            continue
        if name == "mechanical_shock" and not all(
            getattr(phase_args, gate, None) is not None
            for gate in (
                "mechanical_shock_skip_animation_state", "mechanical_shock_task_claims",
                "mechanical_shock_mech_fight_claim_state",
            )
        ):
            reason = (
                "requires current-run --mechanical-shock-skip-animation-state, "
                "--mechanical-shock-task-claims, and --mechanical-shock-mech-fight-claim-state gates"
            )
            results.append(PhaseResult(name, "skipped", reason))
            print(f"daily rewards: skipped {name}: {reason}", flush=True)
            continue
        if name == "mimic_card_library" and not all(
            getattr(phase_args, gate, None) is not None
            for gate in (
                "mimic_skip_animation_state", "mimic_free_draw_state", "mimic_task_claims",
                "mimic_one_click_claim_state",
            )
        ):
            reason = "requires current-run --mimic-skip-animation-state, --mimic-free-draw-state, --mimic-task-claims, and --mimic-one-click-claim-state gates"
            results.append(PhaseResult(name, "skipped", reason))
            print(f"daily rewards: skipped {name}: {reason}", flush=True)
            continue
        try:
            results.append(run_daily_phase(name, handler, phase_args))
        except ClickError as exc:
            results.append(PhaseResult(name, "fatal_failure", str(exc)))
            results.extend(PhaseResult(skipped_name, "skipped") for skipped_name, _ in phases[index + 1 :])
            print_daily_summary(results, task_selection if from_task is not None else None)
            raise
    print_daily_summary(results, task_selection if from_task is not None else None)
    return 0
