#!/usr/bin/env python3
"""CLI entry point for the 向僵尸开炮 WeChat mini game helper."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Dict, Iterable, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from scripts import zombie_common as _common
from scripts.zombie_common import *
from scripts.zombie_actions import *
from scripts.zombie_tasks import base as _base
from scripts.zombie_tasks import daily as _daily
from scripts.zombie_tasks import home as _home
from scripts.zombie_tasks import journey as _journey
from scripts.zombie_tasks import legion as _legion
from scripts.zombie_tasks import patrol as _patrol
from scripts.zombie_tasks import shop as _shop


_TASK_MODULES = (_base, _daily, _home, _journey, _legion, _patrol, _shop)
_TASK_HANDLERS = {
    "command_base_training_hall": _base.command_base_training_hall,
    "command_daily_rewards": _daily.command_daily_rewards,
    "command_calendar_claim": _home.command_calendar_claim,
    "command_mail_claim": _home.command_mail_claim,
    "command_welfare_claim": _home.command_welfare_claim,
    "command_journey_resource_claim": _journey.command_journey_resource_claim,
    "command_legion_daily_rewards": _legion.command_legion_daily_rewards,
    "command_legion_reward_claims": _legion.command_legion_reward_claims,
    "command_legion_sweep_batch": _legion.command_legion_sweep_batch,
    "command_patrol_ads_batch": _patrol.command_patrol_ads_batch,
    "command_patrol_ads_from_home": _patrol.command_patrol_ads_from_home,
    "command_patrol_full_from_home": _patrol.command_patrol_full_from_home,
    "command_patrol_quick_batch": _patrol.command_patrol_quick_batch,
    "command_shop_training_hall": _shop.command_shop_training_hall,
}
_COMMON_BASE = {
    name: getattr(_common, name)
    for name in (
        "front_window_snapshot", "classify_snapshot", "get_bounds", "prepare_command_bounds",
        "fit_game_window", "ensure_unchanged_game_window", "focus_game_window",
        "focus_game_window_at_start", "perform_click", "perform_dismiss_click",
        "sleep_between", "ensure_game_ready_after_ad",
    )
}
_TASK_DEPENDENCIES = (
    "prepare_command_bounds", "perform_click", "perform_dismiss_click", "sleep_between",
    "scale_point", "ensure_game_ready_after_ad", "focus_game_window",
    "ACTIONS", "Bounds", "set_phase_state", "PhaseProgress", "PhaseResult",
    "recover_phase",
)


def _sync_task_compat(module: object) -> None:
    """Keep legacy entry-point monkeypatches effective after task extraction."""
    for name in _TASK_DEPENDENCIES:
        if hasattr(module, name) and name in globals():
            setattr(module, name, globals()[name])
    if module is _daily:
        for name in _TASK_HANDLERS:
            if name != "command_daily_rewards":
                setattr(module, name, globals()[name])
    if module is _legion:
        module.command_legion_reward_claims = globals()["command_legion_reward_claims"]
    for name in (
        "front_window_snapshot", "classify_snapshot", "get_bounds", "prepare_command_bounds",
        "fit_game_window",
        "ensure_unchanged_game_window", "focus_game_window", "focus_game_window_at_start",
        "perform_click", "perform_dismiss_click", "sleep_between", "ensure_game_ready_after_ad",
    ):
        value = globals().get(name)
        if hasattr(module, name) and value is not None and type(value).__module__.startswith("unittest.mock"):
            setattr(module, name, value)


def _task_call(module: object, name: str, args: argparse.Namespace) -> int:
    previous = {dependency: getattr(module, dependency) for dependency in _TASK_DEPENDENCIES if hasattr(module, dependency)}
    previous.update({dependency: getattr(module, dependency) for dependency in _TASK_HANDLERS if hasattr(module, dependency)})
    scroll_previous = getattr(module, "scroll_to_bottom", None)
    scroll_override = globals().get("scroll_to_bottom")
    common_names = (
        "front_window_snapshot", "classify_snapshot", "get_bounds", "prepare_command_bounds",
        "fit_game_window",
        "ensure_unchanged_game_window", "focus_game_window", "focus_game_window_at_start",
        "perform_click", "perform_dismiss_click", "sleep_between", "ensure_game_ready_after_ad",
    )
    task_common_previous = {
        dependency: getattr(module, dependency)
        for dependency in common_names
        if hasattr(module, dependency)
    }
    common_previous = {}
    for dependency in common_names:
        value = globals().get(dependency)
        if value is not None and type(value).__module__.startswith("unittest.mock"):
            common_previous[dependency] = getattr(_common, dependency)
            setattr(_common, dependency, value)
    try:
        # The entry-point scroll wrapper delegates to the extracted base task.
        # Only a test-time monkeypatch should cross this boundary; syncing the
        # wrapper itself back into the task creates wrapper -> wrapper recursion.
        if (
            module is _base
            and scroll_override is not None
            and type(scroll_override).__module__.startswith("unittest.mock")
        ):
            module.scroll_to_bottom = scroll_override
        _sync_task_compat(module)
        return _TASK_HANDLERS[name](args)
    finally:
        for dependency, value in previous.items():
            setattr(module, dependency, value)
        if scroll_previous is not None:
            setattr(module, "scroll_to_bottom", scroll_previous)
        for dependency, value in task_common_previous.items():
            setattr(module, dependency, value)
        for dependency, value in common_previous.items():
            setattr(_common, dependency, value)
        for dependency, value in _COMMON_BASE.items():
            setattr(_common, dependency, value)


def command_base_training_hall(args): return _task_call(_base, "command_base_training_hall", args)
def command_daily_rewards(args): return _task_call(_daily, "command_daily_rewards", args)
def command_calendar_claim(args): return _task_call(_home, "command_calendar_claim", args)
def command_mail_claim(args): return _task_call(_home, "command_mail_claim", args)
def command_welfare_claim(args): return _task_call(_home, "command_welfare_claim", args)
def command_journey_resource_claim(args): return _task_call(_journey, "command_journey_resource_claim", args)
def command_legion_daily_rewards(args): return _task_call(_legion, "command_legion_daily_rewards", args)
def command_legion_reward_claims(args): return _task_call(_legion, "command_legion_reward_claims", args)
def command_legion_sweep_batch(args): return _task_call(_legion, "command_legion_sweep_batch", args)
def command_patrol_ads_batch(args): return _task_call(_patrol, "command_patrol_ads_batch", args)
def command_patrol_ads_from_home(args): return _task_call(_patrol, "command_patrol_ads_from_home", args)
def command_patrol_full_from_home(args): return _task_call(_patrol, "command_patrol_full_from_home", args)
def command_patrol_quick_batch(args): return _task_call(_patrol, "command_patrol_quick_batch", args)
def command_shop_training_hall(args): return _task_call(_shop, "command_shop_training_hall", args)


def _common_call(name, *args, **kwargs):
    for dependency, value in _COMMON_BASE.items():
        setattr(_common, dependency, value)
    for dependency in (
        "run_osascript", "time", "shutil", "subprocess", "click_cgclick_bin", "click_quartz", "click_cliclick",
        "click_system_events", "try_click_backend", "front_window_snapshot", "classify_snapshot",
        "get_bounds", "prepare_command_bounds", "fit_game_window", "ensure_unchanged_game_window", "focus_game_window", "focus_game_window_at_start",
        "ensure_unchanged_game_window", "wait_after_click", "sleep_between",
    ):
        value = globals().get(dependency)
        if dependency != name and value is not None and type(value).__module__.startswith("unittest.mock"):
            setattr(_common, dependency, value)
    try:
        return getattr(_common, name)(*args, **kwargs)
    finally:
        for dependency, value in _COMMON_BASE.items():
            setattr(_common, dependency, value)


# Compatibility re-exports remain callable through the historical module path;
# the implementation and all task modules use zombie_common as the boundary.
def focus_game_window(*args, **kwargs): return _common_call("focus_game_window", *args, **kwargs)
def focus_game_window_at_start(*args, **kwargs): return _common_call("focus_game_window_at_start", *args, **kwargs)
def perform_click(*args, **kwargs): return _common_call("perform_click", *args, **kwargs)
_ENTRY_PERFORM_CLICK = perform_click
def perform_dismiss_click(*args, **kwargs):
    if globals().get("perform_click") is not _ENTRY_PERFORM_CLICK:
        x, y, backend, bounds = args[:4]
        selected = perform_click(x, y, backend, bounds, False)
        time.sleep(DISMISS_POST_WAIT_SECONDS)
        return selected
    return _common_call("perform_dismiss_click", *args, **kwargs)
def ensure_game_ready_after_ad(*args, **kwargs): return _common_call("ensure_game_ready_after_ad", *args, **kwargs)
def click_system_events(*args, **kwargs): return _common_call("click_system_events", *args, **kwargs)
def click_cgclick_bin(*args, **kwargs): return _common_call("click_cgclick_bin", *args, **kwargs)
def click_quartz(*args, **kwargs): return _common_call("click_quartz", *args, **kwargs)
def click_cliclick(*args, **kwargs): return _common_call("click_cliclick", *args, **kwargs)
def scroll_to_bottom(*args, **kwargs):
    _sync_task_compat(_base)
    return _base.scroll_to_bottom(*args, **kwargs)


def dismiss_reward_once(*args, **kwargs):
    _sync_task_compat(_patrol)
    return _patrol.dismiss_reward_once(*args, **kwargs)


def recover_phase(*args, **kwargs):
    _sync_task_compat(_daily)
    return _daily.recover_phase(*args, **kwargs)


PhaseProgress = _daily.PhaseProgress

def action_names() -> Iterable[str]:
    return sorted(ACTIONS)


def print_json(data: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, sort_keys=True))
    else:
        print(data)


def command_list(args: argparse.Namespace) -> int:
    rows = [
        {"name": name, "x": action.x, "y": action.y, "description": action.desc}
        for name, action in sorted(ACTIONS.items())
    ]
    if args.json:
        print_json(rows, True)
    else:
        for row in rows:
            print(f"{row['name']}\t({row['x']},{row['y']})\t{row['description']}")
    return 0


def command_state(args: argparse.Namespace) -> int:
    snapshot = front_window_snapshot()
    snapshot["status"] = classify_snapshot(snapshot)
    snapshot["aspect"] = round(int(snapshot["width"]) / int(snapshot["height"]), 4)
    if args.json:
        print_json(snapshot, True)
    else:
        print(
            f"{snapshot['status']}: {snapshot['app']} {snapshot['bundle']} "
            f"title={snapshot['title']!r} at {snapshot['x']},{snapshot['y']} "
            f"size {snapshot['width']}x{snapshot['height']} aspect {snapshot['aspect']}"
        )
    return 0


def command_bounds(args: argparse.Namespace) -> int:
    bounds = get_bounds(args)
    if args.fit and not args.mock_bounds:
        bounds = fit_game_window()
    validate_bounds(bounds, allow_mock=bool(args.mock_bounds))
    data = {
        "app": bounds.app_name,
        "bundle": bounds.bundle_id,
        "x": bounds.x,
        "y": bounds.y,
        "width": bounds.width,
        "height": bounds.height,
        "aspect": round(bounds.aspect, 4),
    }
    if args.json:
        print_json(data, True)
    else:
        print(
            f"{bounds.app_name} {bounds.bundle_id} "
            f"at {bounds.x},{bounds.y} size {bounds.width}x{bounds.height} "
            f"aspect {bounds.aspect:.4f}"
        )
    return 0


def command_fit_window(args: argparse.Namespace) -> int:
    bounds = fit_game_window()
    validate_bounds(bounds, allow_mock=False)
    if args.json:
        print_json(
            {
                "app": bounds.app_name,
                "bundle": bounds.bundle_id,
                "x": bounds.x,
                "y": bounds.y,
                "width": bounds.width,
                "height": bounds.height,
                "aspect": round(bounds.aspect, 4),
            },
            True,
        )
    else:
        print(
            f"fit {bounds.app_name} {bounds.bundle_id} "
            f"to {bounds.x},{bounds.y} size {bounds.width}x{bounds.height} "
            f"aspect {bounds.aspect:.4f}"
        )
    return 0


def resolve_action(name: str) -> Action:
    try:
        return ACTIONS[name]
    except KeyError as exc:
        raise ClickError(f"unknown action {name!r}; run 'list' for valid names") from exc


def command_dry_run(args: argparse.Namespace) -> int:
    action = resolve_action(args.name)
    bounds = get_bounds(args)
    validate_bounds(bounds, allow_mock=bool(args.mock_bounds))
    x, y = scale_point(action, bounds)
    data = {
        "action": args.name,
        "base": [action.x, action.y],
        "screen": [x, y],
        "bounds": {
            "app": bounds.app_name,
            "bundle": bounds.bundle_id,
            "x": bounds.x,
            "y": bounds.y,
            "width": bounds.width,
            "height": bounds.height,
        },
    }
    if args.json:
        print_json(data, True)
    else:
        print(f"{args.name}: base ({action.x},{action.y}) -> screen ({x},{y})")
    return 0


def command_click(args: argparse.Namespace) -> int:
    action = resolve_action(args.name)
    bounds = prepare_command_bounds(args)
    x, y = scale_point(action, bounds)
    backend = perform_click(x, y, args.backend, bounds)
    print(f"clicked {args.name} at {x},{y} via {backend}")
    return 0


def command_seq(args: argparse.Namespace) -> int:
    if args.times < 1:
        raise ClickError("--times must be >= 1")
    action = resolve_action(args.name)
    bounds = prepare_command_bounds(args)
    x, y = scale_point(action, bounds)
    backend = ""
    for idx in range(args.times):
        backend = perform_click(x, y, args.backend, bounds)
        if idx + 1 < args.times:
            sleep_between(args.interval)
    print(f"clicked {args.name} {args.times} times at {x},{y} via {backend}")
    return 0


def command_self_test(args: argparse.Namespace) -> int:
    mock = Bounds("MOCK", "mock", 10, 20, BASE_WIDTH * 2, BASE_HEIGHT * 2)
    point = scale_point(ACTIONS["reward_dismiss"], mock)
    expected = (10 + 500, 20 + 1640)
    if point != expected:
        raise ClickError(f"scale self-test failed: got {point}, expected {expected}")
    print("self-test ok")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mock-bounds", type=parse_mock_bounds, help="use x,y,width,height instead of live window bounds")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON where supported")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="list known action names")
    list_parser.set_defaults(func=command_list)

    state_parser = sub.add_parser("state", help="classify the game/WeChat window without screenshotting or clicking")
    state_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    state_parser.set_defaults(func=command_state)

    bounds_parser = sub.add_parser("bounds", help="print and validate front-window bounds")
    bounds_parser.add_argument("--fit", action="store_true", help="resize the game window to the calibrated size first")
    bounds_parser.set_defaults(func=command_bounds)

    fit_parser = sub.add_parser("fit-window", help="resize the game window to the calibrated size")
    fit_parser.set_defaults(func=command_fit_window)

    dry_parser = sub.add_parser("dry-run", help="scale an action without clicking")
    dry_parser.add_argument("verb", choices=["click"], help="currently only click dry-runs are supported")
    dry_parser.add_argument("name", choices=action_names())
    dry_parser.set_defaults(func=command_dry_run)

    click_parser = sub.add_parser("click", help="perform one calibrated click")
    click_parser.add_argument("name", choices=action_names())
    click_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    click_parser.set_defaults(func=command_click)

    seq_parser = sub.add_parser("seq", help="perform a repeated calibrated click")
    seq_parser.add_argument("name", choices=action_names())
    seq_parser.add_argument("--times", type=int, required=True)
    seq_parser.add_argument("--interval", type=non_negative_float, default=0.35)
    seq_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    seq_parser.set_defaults(func=command_seq)

    patrol_ads_parser = sub.add_parser(
        "patrol-ads-batch",
        help="blindly run patrol watch-ad cycles without screenshots; use only after the patrol panel is verified",
    )
    patrol_ads_parser.add_argument("--times", type=int, default=5)
    patrol_ads_parser.add_argument("--ad-wait", type=non_negative_float, default=33.0)
    patrol_ads_parser.add_argument("--reward-wait", type=non_negative_float, default=1.2)
    patrol_ads_parser.add_argument("--between", type=non_negative_float, default=0.8)
    patrol_ads_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    patrol_ads_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    patrol_ads_parser.set_defaults(func=command_patrol_ads_batch)

    patrol_full_parser = sub.add_parser(
        "patrol-full-from-home",
        help="run the full patrol truck routine from home without screenshots",
    )
    patrol_full_parser.add_argument("--quick-times", type=int, default=3)
    patrol_full_parser.add_argument("--ad-times", type=int, default=5)
    patrol_full_parser.add_argument("--panel-wait", type=non_negative_float, default=2.0)
    patrol_full_parser.add_argument("--claim-wait", type=non_negative_float, default=2.0)
    patrol_full_parser.add_argument("--dismiss-wait", type=non_negative_float, default=1.0)
    patrol_full_parser.add_argument("--quick-reward-wait", type=non_negative_float, default=4.5)
    patrol_full_parser.add_argument("--quick-between", type=non_negative_float, default=2.0)
    patrol_full_parser.add_argument("--ad-wait", type=non_negative_float, default=33.0)
    patrol_full_parser.add_argument("--ad-close-wait", type=non_negative_float, default=1.2)
    patrol_full_parser.add_argument("--ad-reward-wait", type=non_negative_float, default=1.0)
    patrol_full_parser.add_argument("--ad-between", type=non_negative_float, default=2.0)
    patrol_full_parser.add_argument("--close-wait", type=non_negative_float, default=1.5)
    patrol_full_parser.add_argument("--fit", action=argparse.BooleanOptionalAction, default=True)
    patrol_full_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    patrol_full_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    patrol_full_parser.set_defaults(func=command_patrol_full_from_home)

    patrol_ads_home_parser = sub.add_parser(
        "patrol-ads-from-home",
        help="open patrol from home and run patrol watch-ad cycles without screenshots",
    )
    patrol_ads_home_parser.add_argument("--times", type=int, default=5)
    patrol_ads_home_parser.add_argument("--panel-wait", type=non_negative_float, default=1.0)
    patrol_ads_home_parser.add_argument("--ad-wait", type=non_negative_float, default=33.0)
    patrol_ads_home_parser.add_argument("--reward-wait", type=non_negative_float, default=1.2)
    patrol_ads_home_parser.add_argument("--between", type=non_negative_float, default=0.8)
    patrol_ads_home_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    patrol_ads_home_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    patrol_ads_home_parser.set_defaults(func=command_patrol_ads_from_home)

    patrol_quick_parser = sub.add_parser(
        "patrol-quick-batch",
        help="blindly run normal quick-patrol cycles without screenshots; use only after the count is verified",
    )
    patrol_quick_parser.add_argument("--times", type=int, required=True)
    patrol_quick_parser.add_argument("--reward-wait", type=non_negative_float, default=2.2)
    patrol_quick_parser.add_argument("--between", type=non_negative_float, default=0.8)
    patrol_quick_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    patrol_quick_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    patrol_quick_parser.set_defaults(func=command_patrol_quick_batch)

    mail_parser = sub.add_parser(
        "mail-claim",
        help="open top-right menu, enter mail/notice, click one-click claim, dismiss reward, and close without screenshots",
    )
    mail_parser.add_argument("--menu-wait", type=non_negative_float, default=1.0)
    mail_parser.add_argument("--open-wait", type=non_negative_float, default=1.0)
    mail_parser.add_argument("--reward-wait", type=non_negative_float, default=1.2)
    mail_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    mail_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    mail_parser.set_defaults(func=command_mail_claim)

    calendar_parser = sub.add_parser(
        "calendar-claim",
        help="open calendar, claim its visible free gift, dismiss the reward, and close",
    )
    calendar_parser.add_argument("--open-wait", type=non_negative_float, default=1.0)
    calendar_parser.add_argument("--reward-wait", type=non_negative_float, default=1.2)
    calendar_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    calendar_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    calendar_parser.set_defaults(func=command_calendar_claim)

    welfare_parser = sub.add_parser(
        "welfare-claim",
        help="open welfare, dismiss only its automatic free reward, and return without recharge tabs",
    )
    welfare_parser.add_argument("--open-wait", type=non_negative_float, default=1.0)
    welfare_parser.add_argument("--reward-wait", type=non_negative_float, default=1.2)
    welfare_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    welfare_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    welfare_parser.set_defaults(func=command_welfare_claim)

    journey_parser = sub.add_parser(
        "journey-resource-claim",
        help="open Journey and collect one visible gold and one visible wood resource bubble",
    )
    journey_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    journey_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    journey_parser.set_defaults(func=command_journey_resource_claim)

    base_parser = sub.add_parser(
        "base-training-hall",
        help="run cafeteria, training-hall rescue/crisis, Battlefield Contest, and Element Trial free routes from the base tab",
    )
    base_parser.add_argument("--battle-times", type=int, default=5)
    base_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    base_parser.add_argument("--skip-scroll", action="store_true", help="use after Computer Use has scrolled to the training hall bottom")
    base_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    base_parser.set_defaults(func=command_base_training_hall)

    shop_parser = sub.add_parser(
        "shop-training-hall",
        help="open the shop, claim the free resource gold x600, then claim special-pack gold",
    )
    shop_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    shop_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    shop_parser.set_defaults(func=command_shop_training_hall)

    daily_parser = sub.add_parser(
        "daily-rewards",
        help="run patrol, calendar, welfare, mail, legion, and Journey daily rewards with one checked game window",
    )
    daily_parser.add_argument("--fit", action=argparse.BooleanOptionalAction, default=True)
    daily_parser.add_argument(
        "--from-step",
        type=int,
        choices=range(1, 9),
        default=1,
        metavar="N",
        help="resume at phase 1=patrol, 2=calendar, 3=welfare, 4=mail, 5=legion, 6=journey, 7=base training hall, or 8=shop training hall",
    )
    daily_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    daily_parser.add_argument("--dry-run", action="store_true", help="print all six planned flows without clicking or sleeping")
    daily_parser.set_defaults(func=command_daily_rewards)

    legion_daily_parser = sub.add_parser(
        "legion-daily-rewards",
        help="run the verified daily-cut, two foreign sweeps, and legion reward claim sequence",
    )
    legion_daily_parser.add_argument("--sweep-times", type=int, default=2)
    legion_daily_parser.add_argument("--confirm-wait", type=non_negative_float, default=0.8)
    legion_daily_parser.add_argument("--sweep-reward-wait", type=non_negative_float, default=1.2)
    legion_daily_parser.add_argument("--sweep-between", type=non_negative_float, default=0.6)
    legion_daily_parser.add_argument("--reward-page-wait", type=non_negative_float, default=4.0)
    legion_daily_parser.add_argument("--reward-wait", type=non_negative_float, default=1.0)
    legion_daily_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    legion_daily_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    legion_daily_parser.set_defaults(func=command_legion_daily_rewards)

    legion_reward_parser = sub.add_parser(
        "legion-reward-claims",
        help="run foreign-challenge sweeps and claim the first legion and personal reward entries",
    )
    legion_reward_parser.add_argument("--sweep-times", type=int, default=2)
    legion_reward_parser.add_argument("--confirm-wait", type=non_negative_float, default=0.8)
    legion_reward_parser.add_argument("--sweep-reward-wait", type=non_negative_float, default=1.2)
    legion_reward_parser.add_argument("--sweep-between", type=non_negative_float, default=0.6)
    legion_reward_parser.add_argument("--reward-page-wait", type=non_negative_float, default=4.0)
    legion_reward_parser.add_argument("--reward-wait", type=non_negative_float, default=1.0)
    legion_reward_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    legion_reward_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    legion_reward_parser.set_defaults(func=command_legion_reward_claims)

    legion_sweep_parser = sub.add_parser(
        "legion-sweep-batch",
        help="run verified foreign-challenge sweep cycles without screenshots between cycles",
    )
    legion_sweep_parser.add_argument("--times", type=int, required=True)
    legion_sweep_parser.add_argument("--confirm-wait", type=non_negative_float, default=0.8)
    legion_sweep_parser.add_argument("--reward-wait", type=non_negative_float, default=1.2)
    legion_sweep_parser.add_argument("--between", type=non_negative_float, default=0.6)
    legion_sweep_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    legion_sweep_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    legion_sweep_parser.set_defaults(func=command_legion_sweep_batch)

    test_parser = sub.add_parser("self-test", help="run non-clicking internal checks")
    test_parser.set_defaults(func=command_self_test)

    return parser


def command_requires_focus(args: argparse.Namespace | str) -> bool:
    """Return whether a command needs focus, exempting mock dry-runs."""
    if isinstance(args, str):
        return args not in NON_OPERATING_COMMANDS
    if args.command in NON_OPERATING_COMMANDS:
        return False
    return not (bool(getattr(args, "mock_bounds", None)) and bool(getattr(args, "dry_run", False)))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if (
            getattr(args, "mock_bounds", None)
            and not getattr(args, "dry_run", False)
            and args.command not in {"bounds", "dry-run", "list", "state", "self-test"}
        ):
            raise ClickError("--mock-bounds is simulation-only; add --dry-run instead of executing clicks")
        if command_requires_focus(args):
            focus_game_window_at_start()
        return args.func(args)
    except ClickError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
