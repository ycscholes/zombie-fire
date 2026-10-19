"""拟态牌库每日奖励任务。"""

from __future__ import annotations

import argparse

from ..zombie_common import *
from ..zombie_actions import *
from .resume import report_desktop_task


MIMIC_WAITS = {"entry": 0.5, "task_list": 0.5, "task_refresh": 0.5, "reward_page": 0.5, "ad": 33.0, "ad_close": 2.0}


def command_mimic_card_library(args: argparse.Namespace) -> int:
    """按本次确认的动画、免费抽取、首行可领奖数和红点奖励状态执行流程。"""
    skip_state = getattr(args, "mimic_skip_animation_state", None)
    draw_state = getattr(args, "mimic_free_draw_state", None)
    claim_count = getattr(args, "mimic_task_claims", None)
    one_click_state = getattr(args, "mimic_one_click_claim_state", None)
    if (
        skip_state not in {"checked", "unchecked"}
        or draw_state not in {"available", "claimed"}
        or claim_count is None
        or one_click_state not in {"available", "claimed"}
    ):
        args.task_skipped_reason = "requires current-run confirmation of mimic animation checkbox, free-draw state, task claim count, and one-click reward state"
        report_desktop_task(args, "mimic.card_library", "started")
        print("mimic-card-library skipped: requires current-run --mimic-skip-animation-state, --mimic-free-draw-state, --mimic-task-claims, and --mimic-one-click-claim-state gates")
        report_desktop_task(args, "mimic.card_library", "skipped")
        return 0
    if claim_count < 0:
        raise ClickError("--mimic-task-claims must be >= 0")
    report_desktop_task(args, "mimic.card_library", "started")

    bounds = prepare_command_bounds(args)
    names = (
        "mimic_card_library_entry", "mimic_skip_animation", "mimic_free_draw", "mimic_tasks",
        "mimic_task_claim_first", "mimic_tasks_close", "mimic_rewards_entry", "mimic_rewards_claim",
        "ad_close_top", "reward_dismiss", "back_bottom_left",
    )
    points = scaled_points(bounds, *names)
    if args.dry_run:
        print(
            "mimic-card-library dry-run: "
            f"skip_animation={skip_state}, free_draw={draw_state}, task_claims={claim_count}, "
            f"one_click_claim={one_click_state}, "
            f"waits={MIMIC_WAITS}, points={points}"
        )
        report_desktop_task(args, "mimic.card_library", "completed")
        return 0

    def click(action: str, *, kind: str = "plain") -> str:
        x, y = points[action]
        if kind == "reward":
            return perform_reward_click(x, y, args.backend, bounds)
        if kind == "dismiss":
            return perform_dismiss_click(x, y, args.backend, bounds)
        return perform_click(x, y, args.backend, bounds)

    # 1. 页面跳转点击前标记不确定；投递失败时不猜测页面，也不继续后续阶段。
    set_phase_state(args, "mimic_entry_in_progress")
    click("mimic_card_library_entry")
    set_phase_state(args, "mimic_page_opened")
    sleep_between(MIMIC_WAITS["entry"])
    # 2. 只在本次确认未勾选时点击一次，避免重复切换开关。
    if skip_state == "unchecked":
        click("mimic_skip_animation")
        sleep_between(0.3)
    # 3. 免费抽取至多一次；开始点击失败可退回首页，广告阶段失败则停止后续任务。
    if draw_state == "available":
        def start_free_draw(x: int, y: int, backend: str, expected_bounds: Bounds) -> str:
            set_phase_state(args, "mimic_ad_in_progress")
            result = perform_reward_click(x, y, backend, expected_bounds)
            return result

        run_ad_reward_cycle(
            start_point=points["mimic_free_draw"],
            close_point=points["ad_close_top"],
            dismiss_point=points["reward_dismiss"],
            bounds=bounds,
            backend_name=args.backend,
            ad_wait=MIMIC_WAITS["ad"],
            close_wait=MIMIC_WAITS["ad_close"],
            ensure_ready=True,
            start_click=start_free_draw,
            close_click=perform_click,
            dismiss_click=perform_dismiss_click,
            sleep_fn=sleep_between,
            readiness_fn=ensure_game_ready_after_ad,
        )
        set_phase_state(args, "mimic_page_opened")
    # 4. 打开任务层及领取弹窗前都标为不确定；完成每次领取后回到已知任务页。
    set_phase_state(args, "mimic_tasks_opening")
    click("mimic_tasks")
    set_phase_state(args, "mimic_tasks_opened")
    sleep_between(MIMIC_WAITS["task_list"])
    for index in range(claim_count):
        def claim_task(x: int, y: int, backend: str, expected_bounds: Bounds) -> str:
            set_phase_state(args, "mimic_task_claim_in_progress")
            result = perform_reward_click(x, y, backend, expected_bounds)
            return result

        run_reward_claim_cycle(
            claim_point=points["mimic_task_claim_first"],
            dismiss_point=points["reward_dismiss"],
            bounds=bounds,
            backend_name=args.backend,
            claim_wait=MIMIC_WAITS["task_refresh"],
            claim_click=claim_task,
            dismiss_click=perform_dismiss_click,
            sleep_fn=sleep_between,
        )
        set_phase_state(args, "mimic_tasks_opened")
        print(f"mimic-card-library task claim {index + 1}/{claim_count}: clicked current first claim row", flush=True)
    # 5. 关闭任务列表，进入红点奖励页，仅点击免费的一键领取按钮。
    set_phase_state(args, "mimic_tasks_closing")
    click("mimic_tasks_close")
    set_phase_state(args, "mimic_page_opened")
    sleep_between(0.3)
    set_phase_state(args, "mimic_rewards_opening")
    click("mimic_rewards_entry")
    set_phase_state(args, "mimic_rewards_opened")
    sleep_between(MIMIC_WAITS["reward_page"])

    if one_click_state == "available":
        def claim_free_rewards(x: int, y: int, backend: str, expected_bounds: Bounds) -> str:
            set_phase_state(args, "mimic_reward_claim_in_progress")
            result = perform_reward_click(x, y, backend, expected_bounds)
            return result

        run_reward_claim_cycle(
            claim_point=points["mimic_rewards_claim"],
            dismiss_point=points["reward_dismiss"],
            bounds=bounds,
            backend_name=args.backend,
            claim_wait=MIMIC_WAITS["task_refresh"],
            claim_click=claim_free_rewards,
            dismiss_click=perform_dismiss_click,
            sleep_fn=sleep_between,
        )
        set_phase_state(args, "mimic_rewards_opened")
    else:
        print("mimic-card-library one-click reward already claimed this run; skipped claim", flush=True)
    # 6. 按页面路径依次从奖励页退到牌库、再返回首页。
    set_phase_state(args, "mimic_return_library_in_progress")
    click("back_bottom_left")
    set_phase_state(args, "mimic_page_opened")
    set_phase_state(args, "mimic_return_home_in_progress")
    click("back_bottom_left")
    set_phase_state(args, "mimic_home_returned")
    print(
        f"mimic-card-library complete: skip_animation={skip_state}, free_draw={draw_state}, task_claims={claim_count}, one_click_claim={one_click_state}",
        flush=True,
    )
    report_desktop_task(args, "mimic.card_library", "completed")
    return 0
