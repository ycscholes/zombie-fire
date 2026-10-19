"""通行证与作战计划的免费奖励任务。"""

from __future__ import annotations

from datetime import datetime

from ..zombie_common import *
from ..zombie_actions import *
from .base import scroll_to_bottom
from .resume import report_desktop_task


PASS_WAITS = {"entry": 0.5, "tab": 0.5, "claim_refresh": 1.0}
WEEKDAY_NAMES = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def command_battle_pass_daily(args: argparse.Namespace) -> int:
    """按本次页面确认领取通行证免费一键奖励和作战计划当天签到。"""
    free_state = getattr(args, "free_claim_state", None)
    sign_state = getattr(args, "work_plan_sign_state", None)
    if free_state not in {None, "available", "claimed"}:
        raise ClickError("--free-claim-state must be available or claimed")
    if sign_state not in {None, "available", "claimed"}:
        raise ClickError("--work-plan-sign-state must be available or claimed")

    task_id = "pass.daily"
    missing = []
    if free_state is None:
        missing.append("--free-claim-state")
    if sign_state is None:
        missing.append("--work-plan-sign-state")
    args.task_skipped_reason = (
        "requires current-run page confirmation for " + ", ".join(missing)
        if missing else None
    )
    report_desktop_task(args, task_id, "started")

    local_now = datetime.now().astimezone()
    weekday = local_now.weekday()
    weekday_name = WEEKDAY_NAMES[weekday]
    sign_action = "work_plan_sign" if weekday >= 5 else f"work_plan_sign_day{weekday + 1}"
    needs_free_claim = free_state == "available"
    needs_work_plan_sign = sign_state == "available"

    if not needs_free_claim and not needs_work_plan_sign:
        if missing:
            print(
                f"battle-pass skipped: current-run confirmation missing for {', '.join(missing)}; "
                f"date={local_now.date().isoformat()} {weekday_name}",
                flush=True,
            )
            report_desktop_task(args, task_id, "skipped")
        else:
            print(
                f"battle-pass skipped: free claim and {weekday_name} sign-in are already claimed",
                flush=True,
            )
            report_desktop_task(args, task_id, "completed")
        return 0

    bounds = prepare_command_bounds(args)
    args.active_bounds = bounds
    names = (
        "pass_entry", "pass_free_claim", "work_plan_tab", sign_action,
        "reward_dismiss", "back_bottom_left",
    )
    points = scaled_points(bounds, *names)
    if args.dry_run:
        print(
            "battle-pass dry-run: "
            f"date={local_now.date().isoformat()} {weekday_name}, "
            f"free_claim={free_state}, work_plan_sign={sign_state}, "
            f"sunday_scroll={weekday == 6 and needs_work_plan_sign}, "
            f"waits={PASS_WAITS}, points={points}",
            flush=True,
        )
        report_desktop_task(args, task_id, "skipped" if missing else "completed")
        return 0

    # 1. 从首页进入通行证；只用本次 gate 确认的免费领取状态决定是否点击。
    perform_click(*points["pass_entry"], args.backend, bounds)
    set_phase_state(args, "battle_pass_opened")
    sleep_between(PASS_WAITS["entry"])

    if needs_free_claim:
        # 2. 绿色一键领取复用共享领奖循环；已领或未知状态都不触碰该按钮。
        run_reward_claim_cycle(
            claim_point=points["pass_free_claim"],
            dismiss_point=points["reward_dismiss"],
            bounds=bounds,
            backend_name=args.backend,
            claim_wait=PASS_WAITS["claim_refresh"],
            claim_click=perform_reward_click,
            dismiss_click=perform_dismiss_click,
            sleep_fn=sleep_between,
        )
        print("battle-pass: attempted the confirmed green free one-click claim", flush=True)
    elif free_state == "claimed":
        print("battle-pass: free one-click reward already claimed; skipped", flush=True)

    if needs_work_plan_sign:
        # 3. 进入作战计划标签；只有本次确认当天直免可领时才继续到签到按钮。
        perform_tab_click(*points["work_plan_tab"], args.backend, bounds)
        set_phase_state(args, "battle_pass_work_plan_opened")
        sleep_between(PASS_WAITS["tab"])
        if weekday == 6:
            # 4. 周日签到位在页面下方；沿左侧空边缘只拖动一次，避开奖励和补签按钮。
            args.skip_scroll = False
            scroll_to_bottom(
                args,
                start_action="work_plan_sunday_drag_start",
                end_action="work_plan_sunday_drag_end",
            )
        # 5. 只按本机星期选当天对应行；复用该行的校准 Action 和共享领奖循环。
        run_reward_claim_cycle(
            claim_point=points[sign_action],
            dismiss_point=points["reward_dismiss"],
            bounds=bounds,
            backend_name=args.backend,
            claim_wait=PASS_WAITS["claim_refresh"],
            claim_click=perform_reward_click,
            dismiss_click=perform_dismiss_click,
            sleep_fn=sleep_between,
        )
        print(f"battle-pass: attempted the confirmed direct-free {weekday_name} sign-in", flush=True)
    elif sign_state == "claimed":
        print(f"battle-pass: {weekday_name} sign-in already claimed; skipped", flush=True)

    # 6. 返回首页，供每日主流程的下一阶段继续。
    perform_click(*points["back_bottom_left"], args.backend, bounds)
    print(
        f"battle-pass flow {'partial' if missing else 'complete'}: "
        f"date={local_now.date().isoformat()} {weekday_name}, "
        f"missing_gates={','.join(missing) or 'none'}",
        flush=True,
    )
    report_desktop_task(args, task_id, "skipped" if missing else "completed")
    return 0
