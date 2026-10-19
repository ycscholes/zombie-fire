"""巡逻收益、普通快速巡逻与广告巡逻任务。"""

from __future__ import annotations

from ..zombie_common import *
from ..zombie_actions import *
from .resume import (
    LOCAL_TASK_IDS,
    print_task_selection,
    report_desktop_task,
    select_enabled_task_suffix,
    task_entry_page,
)

BUSINESS_WAITS = {
    "patrol_truck": 0.3,
    "patrol_claim": 1.5,
    "quick_patrol_reward": 0.6,
    "quick_patrol_between": 0.3,
    "patrol_ad_start": 33.0,
    "patrol_ad_close": 2,
    "patrol_ad_between": 0.5,
    "patrol_reward_dismiss": 0.3,
    "patrol_close": 0.3,
}


def _perform_event(
    event: str,
    point: tuple[int, int],
    args: argparse.Namespace,
    bounds: Bounds,
    *,
    kind: str | None = None,
) -> str:
    """巡逻步骤：按照对应业务等待时间执行普通点击、领奖或关闭弹窗。"""
    return perform_action(event, *point, args.backend, bounds, BUSINESS_WAITS, kind=kind)

def command_patrol_ads_batch(args: argparse.Namespace) -> int:
    """广告巡逻：从已打开的巡逻页按指定次数观看广告并关闭奖励弹窗。"""
    if args.times < 1:
        raise ClickError("--times must be >= 1")
    bounds = prepare_command_bounds(args)
    points = scaled_points(bounds, "quick_patrol", "ad_close_top", "reward_dismiss")
    if args.dry_run:
        print(
            "patrol ad batch dry-run: "
            f"times={args.times}, event_waits={BUSINESS_WAITS}, points={points}"
        )
        return 0
    backend = ""
    for index in range(args.times):
        backend = run_ad_reward_cycle(
            start_point=points["quick_patrol"],
            close_point=points["ad_close_top"],
            dismiss_point=points["reward_dismiss"],
            bounds=bounds,
            backend_name=args.backend,
            ad_wait=BUSINESS_WAITS["patrol_ad_start"],
            close_wait=BUSINESS_WAITS["patrol_ad_close"],
            start_click=perform_reward_click,
            close_click=perform_reward_click,
            dismiss_click=perform_dismiss_click,
            sleep_fn=sleep_between,
        )
        print(f"patrol ad {index + 1}/{args.times}: completed shared ad reward cycle via {backend}", flush=True)
        if index + 1 < args.times:
            sleep_between(BUSINESS_WAITS["patrol_ad_between"])
    print(f"patrol ad batch complete: attempted {args.times} via {backend}")
    return 0
def patrol_full_points(bounds: Bounds) -> Dict[str, Tuple[int, int]]:
    """巡逻坐标：按当前窗口尺寸换算领取收益、快速巡逻和广告关闭等点击位置。"""
    return scaled_points(
        bounds,
        "patrol_truck",
        "patrol_claim",
        "quick_patrol",
        "ad_close_top",
        "reward_dismiss",
        "patrol_close",
    )


def dismiss_reward_once(
    args: argparse.Namespace | Dict[str, Tuple[int, int]],
    points: Dict[str, Tuple[int, int]] | str,
    bounds: Bounds,
    *,
    label: str,
) -> str:
    # 奖励弹窗关闭后不再补点同一坐标，避免第二击落到已恢复的游戏页面。
    """巡逻奖励：只点击一次关闭弹窗，避免重复点击落到后方游戏页面。"""
    if isinstance(args, dict):
        backend = run_reward_claim_cycle(
            claim_point=None,
            dismiss_point=args["reward_dismiss"],
            bounds=bounds,
            backend_name=str(points),
            claim_wait=0,
            dismiss_click=perform_dismiss_click,
        )
    else:
        assert isinstance(points, dict)
        backend = run_reward_claim_cycle(
            claim_point=None,
            dismiss_point=points["reward_dismiss"],
            bounds=bounds,
            backend_name=args.backend,
            claim_wait=0,
            dismiss_wait=BUSINESS_WAITS["patrol_reward_dismiss"],
            dismiss_click=perform_dismiss_click,
            sleep_fn=sleep_between,
        )
    print(f"{label}: clicked reward-dismiss once via {backend}", flush=True)
    # 旧的冗余第二次点击保留作校准记录；如日后弹窗行为变化，可据此恢复。
    # backend = _perform_event("patrol_reward_dismiss", points["reward_dismiss"], args, bounds, kind="dismiss")
    # print(f"{label}: clicked reward-dismiss 2/2 via {backend}", flush=True)
    return backend


def command_patrol_full_from_home(args: argparse.Namespace) -> int:
    """完整巡逻：从首页领取巡逻收益，执行指定次数的普通和广告快速巡逻后关闭页面。"""
    selection = select_enabled_task_suffix(
        LOCAL_TASK_IDS["patrol-full-from-home"],
        getattr(args, "from_task", None),
        "patrol-full-from-home",
        getattr(args, "desktop_task_ids", None),
    )
    if not (args.dry_run and getattr(args, "json", False)):
        print_task_selection("patrol-full-from-home", selection, dry_run=args.dry_run)
    if args.quick_times < 0:
        raise ClickError("--quick-times must be >= 0")
    if args.ad_times < 0:
        raise ClickError("--ad-times must be >= 0")
    bounds = get_bounds(args)
    if args.mock_bounds:
        validate_bounds(bounds, allow_mock=True)
    else:
        snapshot = front_window_snapshot()
        status = classify_snapshot(snapshot)
        if status != "game_ready":
            raise ClickError(
                "game window is not ready: "
                f"{status} title={snapshot.get('title')!r} "
                f"app={snapshot.get('app')!r} bundle={snapshot.get('bundle')!r}"
            )
        if args.fit:
            bounds = fit_game_window()
        else:
            bounds = ensure_valid_game_bounds(bounds)
        validate_bounds(bounds, allow_mock=False)
        # The CLI startup gate already focused the game; after an optional fit,
        # bind the final calibrated geometry for the short safe-click session.
        bind_input_session(bounds)
    points = patrol_full_points(bounds)
    if args.dry_run:
        plan = {
            "command": "patrol-full-from-home",
            "tasks": selection.remaining,
            "skipped_tasks": selection.skipped,
            "entry_page": (
                task_entry_page("patrol-full-from-home", selection.selected)
                if selection.explicit_start
                else None
            ),
            "quick_times": args.quick_times,
            "ad_times": args.ad_times,
            "fit": args.fit and not bool(args.mock_bounds),
            "event_waits": BUSINESS_WAITS,
            "points": points,
        }
        if args.json:
            print_json(plan, True)
        else:
            print(
                "patrol full from-home dry-run: "
                f"tasks={selection.remaining}, skipped={selection.skipped}, "
                f"quick_times={args.quick_times}, ad_times={args.ad_times}, "
                f"fit={plan['fit']}, event_waits={plan['event_waits']}, points={points}"
            )
        for task_id in selection.remaining:
            report_desktop_task(args, task_id, "started")
            report_desktop_task(args, task_id, "completed")
        return 0

    tasks = set(selection.remaining)
    if "claim" in tasks:
        report_desktop_task(args, "claim", "started")
        backend = _perform_event("patrol_truck", points["patrol_truck"], args, bounds)
        set_phase_state(args, "patrol_opened")
        print(f"patrol full: clicked patrol truck via {backend}", flush=True)
        backend = _perform_event("patrol_claim", points["patrol_claim"], args, bounds, kind="reward")
        print(f"patrol full: clicked patrol claim via {backend}", flush=True)
        backend = dismiss_reward_once(args, points, bounds, label="patrol full claim")
        report_desktop_task(args, "claim", "completed")
    elif tasks:
        # A resumed quick/ad task starts with the patrol panel already open.
        set_phase_state(args, "patrol_opened")

    if "quick_patrol" in tasks:
        report_desktop_task(args, "quick_patrol", "started")
        for idx in range(args.quick_times):
            backend = _perform_event("quick_patrol_reward", points["quick_patrol"], args, bounds, kind="reward")
            print(f"patrol full quick {idx + 1}/{args.quick_times}: clicked quick-patrol via {backend}", flush=True)
            backend = dismiss_reward_once(
                args,
                points,
                bounds,
                label=f"patrol full quick {idx + 1}/{args.quick_times}",
            )
        report_desktop_task(args, "quick_patrol", "completed")
    if "ad_patrol" in tasks:
        report_desktop_task(args, "ad_patrol", "started")
        for idx in range(args.ad_times):
            backend = run_ad_reward_cycle(
                start_point=points["quick_patrol"],
                close_point=points["ad_close_top"],
                dismiss_point=points["reward_dismiss"],
                bounds=bounds,
                backend_name=args.backend,
                ad_wait=BUSINESS_WAITS["patrol_ad_start"],
                close_wait=BUSINESS_WAITS["patrol_ad_close"],
                ensure_ready=True,
                start_click=perform_click,
                close_click=perform_click,
                dismiss_click=perform_dismiss_click,
                sleep_fn=sleep_between,
                readiness_fn=ensure_game_ready_after_ad,
            )
            # 完整巡逻原有的奖励关闭后业务等待为 0.3 秒，保留该时序。
            sleep_between(BUSINESS_WAITS["patrol_reward_dismiss"])
            print(f"patrol full ad {idx + 1}/{args.ad_times}: completed shared ad reward cycle via {backend}", flush=True)
        report_desktop_task(args, "ad_patrol", "completed")
    backend = _perform_event("patrol_close", points["patrol_close"], args, bounds)
    print(
        f"patrol full complete: attempted {selection.remaining}; "
        f"quick={args.quick_times}, ads={args.ad_times}; "
        f"clicked close via {backend}"
    )
    return 0

def command_patrol_ads_from_home(args: argparse.Namespace) -> int:
    """首页广告巡逻：打开巡逻页，按指定次数观看广告领取奖励后关闭页面。"""
    if args.times < 1:
        raise ClickError("--times must be >= 1")
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "patrol_truck",
        "quick_patrol",
        "ad_close_top",
        "reward_dismiss",
        "patrol_close",
    )
    if args.dry_run:
        print(
            "patrol ad from-home dry-run: "
            f"times={args.times}, event_waits={BUSINESS_WAITS}, points={points}"
        )
        return 0
    backend = _perform_event("patrol_truck", points["patrol_truck"], args, bounds)
    print(f"patrol ad from-home: clicked patrol truck via {backend}", flush=True)
    batch_args = argparse.Namespace(**vars(args))
    batch_args.mock_bounds = bounds
    batch_args.fit = False
    batch_args.from_task = None
    command_patrol_ads_batch(batch_args)
    backend = _perform_event("patrol_close", points["patrol_close"], args, bounds)
    print(f"patrol ad from-home complete: attempted {args.times}; clicked close via {backend}")
    return 0


def command_patrol_quick_batch(args: argparse.Namespace) -> int:
    """普通快速巡逻：从已打开的巡逻页按指定次数领取奖励并关闭弹窗。"""
    if args.times < 1:
        raise ClickError("--times must be >= 1")
    bounds = prepare_command_bounds(args)
    points = scaled_points(bounds, "quick_patrol", "reward_dismiss")
    if args.dry_run:
        print(
            "patrol quick batch dry-run: "
            f"times={args.times}, event_waits={BUSINESS_WAITS}, points={points}"
        )
        return 0
    backend = run_repeated_click_flow(
        points=points,
        bounds=bounds,
        backend_name=args.backend,
        count=args.times,
        between=BUSINESS_WAITS["quick_patrol_between"],
        steps=(
            ("quick_patrol", "quick patrol {index}/{count}: clicked quick-patrol via {backend}", BUSINESS_WAITS["quick_patrol_reward"]),
            ("reward_dismiss", "quick patrol {index}/{count}: clicked reward-dismiss via {backend}", 0),
        ),
    )
    print(f"patrol quick batch complete: attempted {args.times} via {backend}")
    return 0
