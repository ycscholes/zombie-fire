"""武装降临页面的校准领取任务。"""

from __future__ import annotations

import argparse

from ..zombie_common import *
from ..zombie_actions import *
from .resume import report_desktop_task


ARMED_WAITS = {"entry": 0.5, "task_list": 0.5, "task_refresh": 0.5, "tab": 0.5, "ad": 33.0, "ad_close": 2.0}


def command_armed_descent(args: argparse.Namespace) -> int:
    """按本次 Computer Use 确认的动画、免费抽取状态和首行可领奖数执行武装降临七步。"""
    skip_state = getattr(args, "skip_animation_state", None)
    draw_state = getattr(args, "free_draw_state", None)
    claim_count = getattr(args, "task_claims", None)
    if skip_state not in {"checked", "unchecked"} or draw_state not in {"available", "claimed"} or claim_count is None:
        args.task_skipped_reason = "requires current-run confirmation of animation checkbox, free-draw state, and task claim count"
        report_desktop_task(args, "armed.descent", "started")
        print("armed-descent skipped: requires current-run --skip-animation-state, --free-draw-state, and --task-claims gates")
        report_desktop_task(args, "armed.descent", "skipped")
        return 0
    if claim_count < 0:
        raise ClickError("--task-claims must be >= 0")
    report_desktop_task(args, "armed.descent", "started")

    bounds = prepare_command_bounds(args)
    names = (
        "armed_descent_entry", "armed_skip_animation", "armed_free_draw_ad", "armed_tasks",
        "armed_task_claim_first", "armed_tasks_close", "armed_arsenal_tab", "armed_arsenal_claim",
        "ad_close_top", "reward_dismiss", "back_bottom_left",
    )
    points = scaled_points(bounds, *names)
    if args.dry_run:
        print(
            "armed-descent dry-run: "
            f"skip_animation={skip_state}, free_draw={draw_state}, task_claims={claim_count}, "
            f"waits={ARMED_WAITS}, points={points}"
        )
        report_desktop_task(args, "armed.descent", "completed")
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

    # 1. 从首页进入武装降临，并在复选框前等待页面稳定。
    click("armed_descent_entry")
    sleep_between(ARMED_WAITS["entry"])
    # 2. 仅在本次视觉确认未勾选时点一次，已勾选时绝不盲目切换。
    if skip_state == "unchecked":
        click("armed_skip_animation")
        sleep_between(0.3)
    # 3. 免费广告按钮每日只点一次；广告结束检查回到游戏后再关闭奖励。
    if draw_state == "available":
        run_ad_reward_cycle(
            start_point=points["armed_free_draw_ad"],
            close_point=points["ad_close_top"],
            dismiss_point=points["reward_dismiss"],
            bounds=bounds,
            backend_name=args.backend,
            ad_wait=ARMED_WAITS["ad"],
            close_wait=ARMED_WAITS["ad_close"],
            ensure_ready=True,
            start_click=perform_reward_click,
            close_click=perform_click,
            dismiss_click=perform_dismiss_click,
            sleep_fn=sleep_between,
            readiness_fn=ensure_game_ready_after_ad,
        )
    # 4. 列表会在领取后重排；每次仅重复点击经本次确认可领的当前首行。
    click("armed_tasks")
    sleep_between(ARMED_WAITS["task_list"])
    for index in range(claim_count):
        run_reward_claim_cycle(
            claim_point=points["armed_task_claim_first"],
            dismiss_point=points["reward_dismiss"],
            bounds=bounds,
            backend_name=args.backend,
            claim_wait=ARMED_WAITS["task_refresh"],
            claim_click=perform_reward_click,
            dismiss_click=perform_dismiss_click,
            sleep_fn=sleep_between,
        )
        print(f"armed-descent task claim {index + 1}/{claim_count}: clicked current first claim row", flush=True)
    # 5. 关闭任务弹窗；6. 进入武库并一键领取免费奖励；7. 返回首页。
    click("armed_tasks_close")
    sleep_between(0.3)
    click("armed_arsenal_tab", kind="tab")
    sleep_between(ARMED_WAITS["tab"])
    run_reward_claim_cycle(
        claim_point=points["armed_arsenal_claim"],
        dismiss_point=points["reward_dismiss"],
        bounds=bounds,
        backend_name=args.backend,
        claim_wait=ARMED_WAITS["task_refresh"],
        claim_click=perform_reward_click,
        dismiss_click=perform_dismiss_click,
        sleep_fn=sleep_between,
    )
    click("back_bottom_left")
    print(
        f"armed-descent complete: skip_animation={skip_state}, free_draw={draw_state}, task_claims={claim_count}",
        flush=True,
    )
    report_desktop_task(args, "armed.descent", "completed")
    return 0
