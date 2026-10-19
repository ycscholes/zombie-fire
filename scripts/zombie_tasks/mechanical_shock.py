"""机械震荡每日任务：按本次页面观察安全领取任务与机甲械斗奖励。"""

from __future__ import annotations

import argparse

from ..zombie_common import *
from ..zombie_actions import *
from .resume import report_desktop_task


MECHANICAL_SHOCK_WAITS = {"entry": 0.5, "task_list": 0.5, "task_refresh": 0.5, "tab": 0.5}


def command_mechanical_shock(args: argparse.Namespace) -> int:
    """按本次确认的动画勾选、当前首行可领奖数和机甲械斗一键领取状态执行机械震荡。"""
    skip_state = getattr(args, "mechanical_shock_skip_animation_state", None)
    claim_count = getattr(args, "mechanical_shock_task_claims", None)
    mech_fight_state = getattr(args, "mechanical_shock_mech_fight_claim_state", None)
    if (
        skip_state not in {"checked", "unchecked"}
        or claim_count is None
        or mech_fight_state not in {"available", "claimed"}
    ):
        args.task_skipped_reason = (
            "requires current-run confirmation of mechanical-shock animation checkbox, "
            "task claim count, and mech-fight one-click claim state"
        )
        report_desktop_task(args, "mechanical.shock", "started")
        print(
            "mechanical-shock skipped: requires current-run "
            "--mechanical-shock-skip-animation-state, --mechanical-shock-task-claims, "
            "and --mechanical-shock-mech-fight-claim-state gates"
        )
        report_desktop_task(args, "mechanical.shock", "skipped")
        return 0
    if not 0 <= claim_count <= 3:
        raise ClickError("--mechanical-shock-task-claims must be between 0 and 3")
    report_desktop_task(args, "mechanical.shock", "started")

    bounds = prepare_command_bounds(args)
    names = (
        "mechanical_shock_entry", "mechanical_shock_skip_animation", "mechanical_shock_tasks",
        "mechanical_shock_task_claim_first", "mechanical_shock_tasks_close",
        "mechanical_shock_mech_fight_tab", "mechanical_shock_mech_fight_claim",
        "reward_dismiss", "back_bottom_left",
    )
    points = scaled_points(bounds, *names)
    if args.dry_run:
        print(
            "mechanical-shock dry-run: "
            f"skip_animation={skip_state}, task_claims={claim_count}, "
            f"mech_fight_claim={mech_fight_state}, waits={MECHANICAL_SHOCK_WAITS}, points={points}"
        )
        report_desktop_task(args, "mechanical.shock", "completed")
        return 0

    def click(action: str, *, kind: str = "plain") -> str:
        x, y = points[action]
        if kind == "reward":
            return perform_reward_click(x, y, args.backend, bounds)
        if kind == "dismiss":
            return perform_dismiss_click(x, y, args.backend, bounds)
        if kind == "tab":
            return perform_tab_click(x, y, args.backend, bounds)
        return perform_click(x, y, args.backend, bounds)

    # 1. 从首页进入机械震荡；点击中断时恢复动作按进入前后的不确定状态处理。
    set_phase_state(args, "mechanical_shock_entry_in_progress")
    click("mechanical_shock_entry")
    set_phase_state(args, "mechanical_shock_page_opened")
    sleep_between(MECHANICAL_SHOCK_WAITS["entry"])
    # 2. 仅本次确认未勾选时点击跳过动画复选框，已勾选时保持原状态。
    if skip_state == "unchecked":
        set_phase_state(args, "mechanical_shock_animation_in_progress")
        click("mechanical_shock_skip_animation")
        set_phase_state(args, "mechanical_shock_page_opened")
        sleep_between(0.3)
    # 3. 任务列表会在领取后重排；只按本次确认数量领取当前首行并关闭对应奖励。
    set_phase_state(args, "mechanical_shock_tasks_opening")
    click("mechanical_shock_tasks")
    set_phase_state(args, "mechanical_shock_tasks_opened")
    sleep_between(MECHANICAL_SHOCK_WAITS["task_list"])
    for index in range(claim_count):
        def claim_current_first_row(x: int, y: int, backend: str, expected_bounds: Bounds) -> str:
            set_phase_state(args, "mechanical_shock_task_claim_in_progress")
            return perform_reward_click(x, y, backend, expected_bounds)

        run_reward_claim_cycle(
            claim_point=points["mechanical_shock_task_claim_first"],
            dismiss_point=points["reward_dismiss"],
            bounds=bounds,
            backend_name=args.backend,
            claim_wait=MECHANICAL_SHOCK_WAITS["task_refresh"],
            claim_click=claim_current_first_row,
            dismiss_click=perform_dismiss_click,
            sleep_fn=sleep_between,
        )
        set_phase_state(args, "mechanical_shock_tasks_opened")
        print(
            f"mechanical-shock task claim {index + 1}/{claim_count}: "
            "clicked current first claim row",
            flush=True,
        )
    # 4. 关闭任务弹窗，进入右下机甲械斗页签；只在本次确认可领时一键领取。
    set_phase_state(args, "mechanical_shock_tasks_closing")
    click("mechanical_shock_tasks_close")
    set_phase_state(args, "mechanical_shock_page_opened")
    sleep_between(0.3)
    set_phase_state(args, "mechanical_shock_mech_fight_opening")
    click("mechanical_shock_mech_fight_tab", kind="tab")
    set_phase_state(args, "mechanical_shock_mech_fight_opened")
    sleep_between(MECHANICAL_SHOCK_WAITS["tab"])
    if mech_fight_state == "available":
        def claim_mech_fight_rewards(x: int, y: int, backend: str, expected_bounds: Bounds) -> str:
            set_phase_state(args, "mechanical_shock_mech_fight_claim_in_progress")
            return perform_reward_click(x, y, backend, expected_bounds)

        run_reward_claim_cycle(
            claim_point=points["mechanical_shock_mech_fight_claim"],
            dismiss_point=points["reward_dismiss"],
            bounds=bounds,
            backend_name=args.backend,
            claim_wait=MECHANICAL_SHOCK_WAITS["task_refresh"],
            claim_click=claim_mech_fight_rewards,
            dismiss_click=perform_dismiss_click,
            sleep_fn=sleep_between,
        )
        set_phase_state(args, "mechanical_shock_mech_fight_opened")
    else:
        print("mechanical-shock mech-fight one-click reward already claimed this run; skipped claim", flush=True)
    # 5. 从机甲械斗页使用校准的左下返回键回到游戏首页。
    set_phase_state(args, "mechanical_shock_home_return_in_progress")
    click("back_bottom_left")
    set_phase_state(args, "mechanical_shock_home_returned")
    print(
        f"mechanical-shock complete: skip_animation={skip_state}, task_claims={claim_count}, "
        f"mech_fight_claim={mech_fight_state}",
        flush=True,
    )
    report_desktop_task(args, "mechanical.shock", "completed")
    return 0
