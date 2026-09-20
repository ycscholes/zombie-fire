"""Patrol tab workflows."""

from __future__ import annotations

from ..zombie_common import *
from ..zombie_actions import *

BUSINESS_WAITS = {
    "patrol_truck": 0.3,
    "patrol_claim": 0.3,
    "quick_patrol_reward": 0.3,
    "quick_patrol_between": 0.3,
    "patrol_ad_start": 33.0,
    "patrol_ad_close": 1.5,
    "patrol_ad_between": 0.5,
    "patrol_close": 0.3,
}

def command_patrol_ads_batch(args: argparse.Namespace) -> int:
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
    backend = run_repeated_click_flow(
        points=points,
        bounds=bounds,
        backend_name=args.backend,
        count=args.times,
        between=BUSINESS_WAITS["patrol_ad_between"],
        steps=(
            ("quick_patrol", "patrol ad {index}/{count}: clicked watch-ad via {backend}", BUSINESS_WAITS["patrol_ad_start"]),
            ("ad_close_top", "patrol ad {index}/{count}: clicked ad-close via {backend}", BUSINESS_WAITS["patrol_ad_close"]),
            ("reward_dismiss", "patrol ad {index}/{count}: clicked reward-dismiss via {backend}", 0),
        ),
    )
    print(f"patrol ad batch complete: attempted {args.times} via {backend}")
    return 0
def patrol_full_points(bounds: Bounds) -> Dict[str, Tuple[int, int]]:
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
    points: Dict[str, Tuple[int, int]],
    backend_name: str,
    bounds: Bounds,
    *,
    label: str,
) -> str:
    # 奖励弹窗关闭后不再补点同一坐标，避免第二击落到已恢复的游戏页面。
    backend = perform_dismiss_click(*points["reward_dismiss"], backend_name, bounds)
    print(f"{label}: clicked reward-dismiss once via {backend}", flush=True)
    # 旧的冗余第二次点击保留作校准记录；如日后弹窗行为变化，可据此恢复。
    # backend = perform_click(*points["reward_dismiss"], backend_name, bounds)
    # print(f"{label}: clicked reward-dismiss 2/2 via {backend}", flush=True)
    return backend


def command_patrol_full_from_home(args: argparse.Namespace) -> int:
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
                f"quick_times={args.quick_times}, ad_times={args.ad_times}, "
                f"fit={plan['fit']}, event_waits={plan['event_waits']}, points={points}"
            )
        return 0

    backend = perform_click(*points["patrol_truck"], args.backend, bounds)
    set_phase_state(args, "patrol_opened")
    print(f"patrol full: clicked patrol truck via {backend}", flush=True)
    sleep_between(BUSINESS_WAITS["patrol_truck"])

    backend = perform_reward_click(*points["patrol_claim"], args.backend, bounds)
    print(f"patrol full: clicked patrol claim via {backend}", flush=True)
    sleep_between(BUSINESS_WAITS["patrol_claim"])
    backend = dismiss_reward_once(points, args.backend, bounds, label="patrol full claim")
    sleep_between(BUSINESS_WAITS["quick_patrol_between"])

    for idx in range(args.quick_times):
        backend = perform_reward_click(*points["quick_patrol"], args.backend, bounds)
        print(f"patrol full quick {idx + 1}/{args.quick_times}: clicked quick-patrol via {backend}", flush=True)
        sleep_between(BUSINESS_WAITS["quick_patrol_reward"])
        backend = dismiss_reward_once(
            points,
            args.backend,
            bounds,
            label=f"patrol full quick {idx + 1}/{args.quick_times}",
        )
        if idx + 1 < args.quick_times:
            sleep_between(BUSINESS_WAITS["quick_patrol_between"])

    sleep_between(BUSINESS_WAITS["patrol_ad_between"])
    for idx in range(args.ad_times):
        backend = perform_click(*points["quick_patrol"], args.backend, bounds)
        print(f"patrol full ad {idx + 1}/{args.ad_times}: clicked watch-ad via {backend}", flush=True)
        sleep_between(BUSINESS_WAITS["patrol_ad_start"])
        backend = perform_click(*points["ad_close_top"], args.backend, bounds)
        print(f"patrol full ad {idx + 1}/{args.ad_times}: clicked ad-close-top via {backend}", flush=True)
        sleep_between(BUSINESS_WAITS["patrol_ad_close"])
        ensure_game_ready_after_ad(bounds)
        backend = dismiss_reward_once(
            points,
            args.backend,
            bounds,
            label=f"patrol full ad {idx + 1}/{args.ad_times}",
        )
        if idx + 1 < args.ad_times:
            sleep_between(BUSINESS_WAITS["patrol_ad_between"])

    sleep_between(BUSINESS_WAITS["patrol_close"])
    backend = perform_click(*points["patrol_close"], args.backend, bounds)
    print(
        "patrol full complete: "
        f"attempted claim, quick={args.quick_times}, ads={args.ad_times}; "
        f"clicked close via {backend}"
    )
    return 0

def command_patrol_ads_from_home(args: argparse.Namespace) -> int:
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
    backend = perform_click(*points["patrol_truck"], args.backend, bounds)
    print(f"patrol ad from-home: clicked patrol truck via {backend}", flush=True)
    sleep_between(BUSINESS_WAITS["patrol_truck"])
    backend = run_repeated_click_flow(
        points=points,
        bounds=bounds,
        backend_name=args.backend,
        count=args.times,
        between=BUSINESS_WAITS["patrol_ad_between"],
        steps=(
            ("quick_patrol", "patrol ad {index}/{count}: clicked watch-ad via {backend}", BUSINESS_WAITS["patrol_ad_start"]),
            ("ad_close_top", "patrol ad {index}/{count}: clicked ad-close via {backend}", BUSINESS_WAITS["patrol_ad_close"]),
            ("reward_dismiss", "patrol ad {index}/{count}: clicked reward-dismiss via {backend}", 0),
        ),
    )
    backend = perform_click(*points["patrol_close"], args.backend, bounds)
    print(f"patrol ad from-home complete: attempted {args.times}; clicked close via {backend}")
    return 0


def command_patrol_quick_batch(args: argparse.Namespace) -> int:
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
