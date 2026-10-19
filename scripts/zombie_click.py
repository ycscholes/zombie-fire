#!/usr/bin/env python3
"""CLI entry point for the 向僵尸开炮 WeChat mini game helper."""

from __future__ import annotations

import argparse
import builtins
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
from scripts.zombie_tasks import battle_pass as _battle_pass
from scripts.zombie_tasks import armed as _armed
from scripts.zombie_tasks import daily as _daily
from scripts.zombie_tasks import home as _home
from scripts.zombie_tasks import journey as _journey
from scripts.zombie_tasks import legion as _legion
from scripts.zombie_tasks import mimic as _mimic
from scripts.zombie_tasks import mechanical_shock as _mechanical_shock
from scripts.zombie_tasks import patrol as _patrol
from scripts.zombie_tasks.resume import DAILY_TASK_IDS, LOCAL_TASK_IDS, task_entry_help
from scripts.zombie_tasks import shop as _shop


_TASK_MODULES = (_armed, _base, _battle_pass, _daily, _home, _journey, _legion, _mechanical_shock, _mimic, _patrol, _shop)
_TASK_HANDLERS = {
    "command_base_training_hall": _base.command_base_training_hall,
    "command_base_training_hall_deep_abyss": _base.command_base_training_hall_deep_abyss,
    "command_base_training_hall_global_rescue": _base.command_base_training_hall_global_rescue,
    "command_base_training_hall_global_expedition": _base.command_base_training_hall_global_expedition,
    "command_base_training_hall_terminal_crisis": _base.command_base_training_hall_terminal_crisis,
    "command_base_training_hall_battlefield_contest": _base.command_base_training_hall_battlefield_contest,
    "command_base_training_hall_element_trial": _base.command_base_training_hall_element_trial,
    "command_base_training_hall_shop": _base.command_base_training_hall_shop,
    "command_daily_rewards": _daily.command_daily_rewards,
    "command_battle_pass_daily": _battle_pass.command_battle_pass_daily,
    "command_armed_descent": _armed.command_armed_descent,
    "command_mechanical_shock": _mechanical_shock.command_mechanical_shock,
    "command_mimic_card_library": _mimic.command_mimic_card_library,
    "command_calendar_claim": _home.command_calendar_claim,
    "command_mail_claim": _home.command_mail_claim,
    "command_welfare_claim": _home.command_welfare_claim,
    "command_journey_daily_rewards": _journey.command_journey_daily_rewards,
    "command_journey_purifier_recruit": _journey.command_journey_purifier_recruit,
    "command_journey_resource_claim": _journey.command_journey_resource_claim,
    "command_legion_daily_rewards": _legion.command_legion_daily_rewards,
    "command_legion_reward_claims": _legion.command_legion_reward_claims,
    "command_legion_sweep_batch": _legion.command_legion_sweep_batch,
    "command_legion_journey_gifts": _legion.command_legion_journey_gifts,
    "command_legion_shop_purchases": _legion.command_legion_shop_purchases,
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
        "focus_game_window_at_start", "perform_click", "perform_dismiss_click", "perform_reward_click", "perform_tab_click", "perform_action", "perform_drag", "drag_cgclick_bin",
        "sleep_between", "ensure_game_ready_after_ad",
        "run_ad_reward_cycle", "run_reward_claim_cycle",
    )
}
_TASK_DEPENDENCIES = (
        "prepare_command_bounds", "perform_click", "perform_dismiss_click", "perform_reward_click", "perform_tab_click", "perform_action", "sleep_between",
    "scale_point", "ensure_game_ready_after_ad", "focus_game_window", "perform_drag", "drag_cgclick_bin",
    "ACTIONS", "Bounds", "set_phase_state", "PhaseProgress", "PhaseResult",
    "recover_phase",
    "run_ad_reward_cycle", "run_reward_claim_cycle",
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
    if module is _journey:
        module.command_journey_resource_claim = globals()["command_journey_resource_claim"]
        module.command_journey_purifier_recruit = globals()["command_journey_purifier_recruit"]
    for name in (
        "front_window_snapshot", "classify_snapshot", "get_bounds", "prepare_command_bounds",
        "fit_game_window",
        "ensure_unchanged_game_window", "focus_game_window", "focus_game_window_at_start",
        "perform_click", "perform_dismiss_click", "perform_reward_click", "perform_tab_click", "perform_action", "perform_drag", "sleep_between", "ensure_game_ready_after_ad", "drag_cgclick_bin",
        "run_ad_reward_cycle", "run_reward_claim_cycle",
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
        "perform_click", "perform_dismiss_click", "perform_reward_click", "perform_tab_click", "perform_action", "perform_drag", "sleep_between", "ensure_game_ready_after_ad", "drag_cgclick_bin",
    )
    task_common_previous = {
        dependency: getattr(module, dependency)
        for dependency in common_names
        if hasattr(module, dependency)
    }
    base_previous = (
        {dependency: getattr(_base, dependency) for dependency in _TASK_DEPENDENCIES if hasattr(_base, dependency)}
        if module is _battle_pass else {}
    )
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
            module in {_base, _battle_pass}
            and scroll_override is not None
            and type(scroll_override).__module__.startswith("unittest.mock")
        ):
            module.scroll_to_bottom = scroll_override
        if module is _battle_pass:
            _sync_task_compat(_base)
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
        for dependency, value in base_previous.items():
            setattr(_base, dependency, value)


# 基地每日任务：领取食堂奖励，依次执行训练大厅各挑战和玩法商店购买。
def command_base_training_hall(args): return _task_call(_base, "command_base_training_hall", args)
# 从已打开的训练大厅列表单独执行深渊挑战子任务。
def command_base_training_hall_deep_abyss(args): return _task_call(_base, "command_base_training_hall_deep_abyss", args)
# 从已打开的训练大厅列表单独执行寰球救援子任务。
def command_base_training_hall_global_rescue(args): return _task_call(_base, "command_base_training_hall_global_rescue", args)
# 从已打开的训练大厅列表单独执行寰球远征子任务。
def command_base_training_hall_global_expedition(args): return _task_call(_base, "command_base_training_hall_global_expedition", args)
# 从已打开的训练大厅列表单独执行终末危机子任务。
def command_base_training_hall_terminal_crisis(args): return _task_call(_base, "command_base_training_hall_terminal_crisis", args)
# 从已打开的训练大厅列表单独执行战场争霸，扫荡次数由 battle_times 指定。
def command_base_training_hall_battlefield_contest(args): return _task_call(_base, "command_base_training_hall_battlefield_contest", args)
# 从已打开的训练大厅列表单独执行元素试炼子任务。
def command_base_training_hall_element_trial(args): return _task_call(_base, "command_base_training_hall_element_trial", args)
# 玩法商店：从训练大厅进入，购买强化剂、枪械图纸和基建耗材后关闭商店。
def command_base_training_hall_shop(args): return _task_call(_base, "command_base_training_hall_shop", args)
# 每日奖励总任务：依次执行十二个阶段，保留旧 from-step 映射并支持按任务继续。
def command_daily_rewards(args): return _task_call(_daily, "command_daily_rewards", args)
# 通行证：按本次确认领取绿色免费一键奖励和当天作战计划直免签到后返回首页。
def command_battle_pass_daily(args): return _task_call(_battle_pass, "command_battle_pass_daily", args)
# 武装降临：仅按本次确认的动画、免费广告和任务可领奖数 gate 执行七步。
def command_armed_descent(args): return _task_call(_armed, "command_armed_descent", args)
# 机械震荡：按本次页面确认的动画、任务首行数和机甲械斗奖励 gate 执行。
def command_mechanical_shock(args): return _task_call(_mechanical_shock, "command_mechanical_shock", args)
# 拟态牌库：按本次确认的动画、免费抽取、任务可领奖数和红点奖励状态领取免费奖励。
def command_mimic_card_library(args): return _task_call(_mimic, "command_mimic_card_library", args)
# 日历：领取当前可见的免费礼包后返回首页。
def command_calendar_claim(args): return _task_call(_home, "command_calendar_claim", args)
# 邮件：打开右上角菜单，一键领取邮件奖励后关闭邮件和菜单。
def command_mail_claim(args): return _task_call(_home, "command_mail_claim", args)
# 福利：拖动右侧菜单进入福利页，关闭自动免费奖励弹窗后返回。
def command_welfare_claim(args): return _task_call(_home, "command_welfare_claim", args)
# 征途每日任务：依次领取资源和执行净化者招募。
def command_journey_daily_rewards(args): return _task_call(_journey, "command_journey_daily_rewards", args)
# 净化者招募：进入征途招募页面，执行一键招募并领取奖励。
def command_journey_purifier_recruit(args): return _task_call(_journey, "command_journey_purifier_recruit", args)
# 征途资源：进入征途，分别领取金币和木材并关闭奖励弹窗。
def command_journey_resource_claim(args): return _task_call(_journey, "command_journey_resource_claim", args)
# 军团每日任务：依次执行每日一刀、异域挑战领奖、商店购买和征途赠礼。
def command_legion_daily_rewards(args): return _task_call(_legion, "command_legion_daily_rewards", args)
# 军团领奖：按指定次数扫荡异域挑战，再领取军团和个人奖励。
def command_legion_reward_claims(args): return _task_call(_legion, "command_legion_reward_claims", args)
# 军团批量扫荡：从已打开的挑战页重复扫荡、确认并关闭奖励弹窗。
def command_legion_sweep_batch(args): return _task_call(_legion, "command_legion_sweep_batch", args)
# 军团征途：领取首个赠礼并尝试三次搜索扫荡，经地图基地返回军团页。
def command_legion_journey_gifts(args): return _task_call(_legion, "command_legion_journey_gifts", args)
# 军团商店：滚动到底部，依次购买枪械图纸、基建粉末和强化剂后关闭商店。
def command_legion_shop_purchases(args): return _task_call(_legion, "command_legion_shop_purchases", args)
# 广告巡逻：从已打开的巡逻页按指定次数观看广告并关闭奖励弹窗。
def command_patrol_ads_batch(args): return _task_call(_patrol, "command_patrol_ads_batch", args)
# 首页广告巡逻：打开巡逻页，按指定次数观看广告领取奖励后关闭页面。
def command_patrol_ads_from_home(args): return _task_call(_patrol, "command_patrol_ads_from_home", args)
# 完整巡逻：从首页领取巡逻收益，执行指定次数的普通和广告快速巡逻后关闭页面。
def command_patrol_full_from_home(args): return _task_call(_patrol, "command_patrol_full_from_home", args)
# 普通快速巡逻：从已打开的巡逻页按指定次数领取奖励并关闭弹窗。
def command_patrol_quick_batch(args): return _task_call(_patrol, "command_patrol_quick_batch", args)
# 商城免费奖励：领取资源页和特惠礼包页的免费金币。
def command_shop_training_hall(args): return _task_call(_shop, "command_shop_training_hall", args)


def _add_from_task_argument(parser: argparse.ArgumentParser, scope: str) -> None:
    parser.add_argument(
        "--from-task",
        choices=LOCAL_TASK_IDS[scope],
        metavar="TASK",
        help=f"resume at TASK and continue; required entry pages by ID: {task_entry_help(scope)}",
    )


def _common_call(name, *args, **kwargs):
    for dependency, value in _COMMON_BASE.items():
        setattr(_common, dependency, value)
    for dependency in (
        "run_osascript", "time", "shutil", "subprocess", "click_cgclick_bin", "click_quartz", "click_cliclick",
        "click_system_events", "try_click_backend", "drag_cgclick_bin", "front_window_snapshot", "classify_snapshot",
        "get_bounds", "prepare_command_bounds", "fit_game_window", "ensure_unchanged_game_window", "focus_game_window", "focus_game_window_at_start",
        "perform_click", "perform_reward_click", "perform_tab_click", "ensure_unchanged_game_window", "wait_after_click", "wait_after_tab_click", "sleep_between",
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
def perform_reward_click(*args, **kwargs): return _common_call("perform_reward_click", *args, **kwargs)
def perform_tab_click(*args, **kwargs): return _common_call("perform_tab_click", *args, **kwargs)
def perform_action(*args, **kwargs): return _common_call("perform_action", *args, **kwargs)
def start_input_session(*args, **kwargs): return _common_call("start_input_session", *args, **kwargs)
def bind_input_session(*args, **kwargs): return _common_call("bind_input_session", *args, **kwargs)
def end_input_session(*args, **kwargs): return _common_call("end_input_session", *args, **kwargs)
_ENTRY_PERFORM_CLICK = perform_click
def perform_dismiss_click(*args, **kwargs):
    if globals().get("perform_click") is not _ENTRY_PERFORM_CLICK:
        x, y, backend, bounds = args[:4]
        return perform_click(x, y, backend, bounds, False)
    return _common_call("perform_dismiss_click", *args, **kwargs)
def perform_drag(*args, **kwargs): return _common_call("perform_drag", *args, **kwargs)
def ensure_game_ready_after_ad(*args, **kwargs): return _common_call("ensure_game_ready_after_ad", *args, **kwargs)
def click_system_events(*args, **kwargs): return _common_call("click_system_events", *args, **kwargs)
def click_cgclick_bin(*args, **kwargs): return _common_call("click_cgclick_bin", *args, **kwargs)
def click_quartz(*args, **kwargs): return _common_call("click_quartz", *args, **kwargs)
def click_cliclick(*args, **kwargs): return _common_call("click_cliclick", *args, **kwargs)
def scroll_to_bottom(*args, **kwargs):
    """基地列表：按校准坐标向上拖动；指定跳过滚动时直接返回。"""
    _sync_task_compat(_base)
    return _base.scroll_to_bottom(*args, **kwargs)


def dismiss_reward_once(*args, **kwargs):
    """巡逻奖励：只点击一次关闭弹窗，避免重复点击落到后方游戏页面。"""
    _sync_task_compat(_patrol)
    return _patrol.dismiss_reward_once(*args, **kwargs)


def recover_phase(*args, **kwargs):
    """阶段恢复：根据已记录的页面状态，尝试退出失败阶段到已知安全位置。"""
    _sync_task_compat(_daily)
    return _daily.recover_phase(*args, **kwargs)


PhaseProgress = _daily.PhaseProgress

def action_names() -> Iterable[str]:
    return sorted(ACTIONS)


def print_json(data: object, as_json: bool) -> None:
    if as_json:
        builtins.print(json.dumps(data, ensure_ascii=False, sort_keys=True))
    else:
        print(data)


def command_list(args: argparse.Namespace) -> int:
    """列出所有已校准动作的名称、坐标和说明。"""
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
    """读取当前前台窗口并输出游戏就绪状态。"""
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
    """读取并校验游戏窗口位置和尺寸，按参数选择是否调整窗口。"""
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
    """将游戏窗口调整到校准尺寸并输出最终位置。"""
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
    session_started = False
    try:
        return ACTIONS[name]
    except KeyError as exc:
        raise ClickError(f"unknown action {name!r}; run 'list' for valid names") from exc


def command_dry_run(args: argparse.Namespace) -> int:
    """动作预演：输出指定动作的基准坐标和屏幕坐标，不执行点击。"""
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
    """单次动作：校验窗口并执行指定动作。"""
    action = resolve_action(args.name)
    bounds = prepare_command_bounds(args)
    x, y = scale_point(action, bounds)
    backend = perform_action(args.name, x, y, args.backend, bounds)
    print(f"clicked {args.name} at {x},{y} via {backend}")
    return 0


def command_seq(args: argparse.Namespace) -> int:
    """重复动作：按指定次数和间隔执行同一个动作。"""
    if args.times < 1:
        raise ClickError("--times must be >= 1")
    action = resolve_action(args.name)
    bounds = prepare_command_bounds(args)
    x, y = scale_point(action, bounds)
    backend = ""
    for idx in range(args.times):
        backend = perform_action(args.name, x, y, args.backend, bounds)
        if idx + 1 < args.times:
            sleep_between(args.interval)
    print(f"clicked {args.name} {args.times} times at {x},{y} via {backend}")
    return 0


def command_self_test(args: argparse.Namespace) -> int:
    """坐标自检：使用模拟窗口验证坐标缩放结果，不操作游戏。"""
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
    patrol_ads_parser.add_argument("--reward-wait", type=non_negative_float, default=0.5)
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
    patrol_full_parser.add_argument("--panel-wait", type=non_negative_float, default=0.3)
    patrol_full_parser.add_argument("--claim-wait", type=non_negative_float, default=0.3)
    patrol_full_parser.add_argument("--dismiss-wait", type=non_negative_float, default=0.3)
    patrol_full_parser.add_argument("--quick-reward-wait", type=non_negative_float, default=0.3)
    patrol_full_parser.add_argument("--quick-between", type=non_negative_float, default=0.3)
    patrol_full_parser.add_argument("--ad-wait", type=non_negative_float, default=33.0)
    patrol_full_parser.add_argument("--ad-close-wait", type=non_negative_float, default=0.5)
    patrol_full_parser.add_argument("--ad-reward-wait", type=non_negative_float, default=1.0)
    patrol_full_parser.add_argument("--ad-between", type=non_negative_float, default=0.5)
    patrol_full_parser.add_argument("--close-wait", type=non_negative_float, default=0.3)
    patrol_full_parser.add_argument("--fit", action=argparse.BooleanOptionalAction, default=True)
    _add_from_task_argument(patrol_full_parser, "patrol-full-from-home")
    patrol_full_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    patrol_full_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    patrol_full_parser.set_defaults(func=command_patrol_full_from_home)

    # 武装降临：gate 必须来自本次 Computer Use 页面确认；无 gate 时任务安全跳过。
    armed_parser = sub.add_parser("armed-descent", help="按已确认 gate 执行武装降临七步免费奖励")
    armed_parser.add_argument("--skip-animation-state", choices=("checked", "unchecked"))
    armed_parser.add_argument("--free-draw-state", choices=("available", "claimed"))
    armed_parser.add_argument("--task-claims", type=int, help="本次确认当前首行可领取的连续条数，可为 0")
    armed_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    armed_parser.add_argument("--dry-run", action="store_true", help="打印执行计划，不点击或等待")
    armed_parser.set_defaults(func=command_armed_descent)

    # 机械震荡独立入口：三项状态必须来自本次页面观察，任务首行最多确认三条。
    mechanical_shock_parser = sub.add_parser("mechanical-shock", help="按本次确认 gate 执行机械震荡每日奖励")
    mechanical_shock_parser.add_argument("--mechanical-shock-skip-animation-state", choices=("checked", "unchecked"))
    mechanical_shock_parser.add_argument("--mechanical-shock-task-claims", type=int, help="本次确认当前首行可领取的连续条数，范围 0 到 3")
    mechanical_shock_parser.add_argument("--mechanical-shock-mech-fight-claim-state", choices=("available", "claimed"), help="机甲械斗页一键领取状态的本次观察")
    mechanical_shock_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    mechanical_shock_parser.add_argument("--dry-run", action="store_true", help="打印执行计划，不点击或等待")
    mechanical_shock_parser.set_defaults(func=command_mechanical_shock)

    # 通行证独立入口：两个领取按钮分别要求本次页面观察，缺失状态时不点击对应按钮。
    pass_parser = sub.add_parser("battle-pass-daily", help="按本次确认领取通行证免费奖励和当天作战计划签到")
    pass_parser.add_argument("--free-claim-state", choices=("available", "claimed"), help="通行证绿色一键领取状态的本次页面观察")
    pass_parser.add_argument("--work-plan-sign-state", choices=("available", "claimed"), help="当天作战计划直免签到状态的本次页面观察")
    pass_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    pass_parser.add_argument("--dry-run", action="store_true", help="打印当天签到计划，不点击或等待")
    pass_parser.set_defaults(func=command_battle_pass_daily)

    # 独立拟态牌库入口：每次运行都要求显式传入四项当前页面观察值。
    mimic_parser = sub.add_parser("mimic-card-library", help="按本次确认执行拟态牌库免费奖励任务")
    mimic_parser.add_argument("--mimic-skip-animation-state", choices=("checked", "unchecked"))
    mimic_parser.add_argument("--mimic-free-draw-state", choices=("available", "claimed"))
    mimic_parser.add_argument("--mimic-task-claims", type=int, help="本次确认当前首行可领取的连续条数，可为 0")
    mimic_parser.add_argument("--mimic-one-click-claim-state", choices=("available", "claimed"), help="拟态牌库红点页一键奖励的本次观察状态")
    mimic_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    mimic_parser.add_argument("--dry-run", action="store_true", help="打印执行计划，不点击或等待")
    mimic_parser.set_defaults(func=command_mimic_card_library)

    patrol_ads_home_parser = sub.add_parser(
        "patrol-ads-from-home",
        help="open patrol from home and run patrol watch-ad cycles without screenshots",
    )
    patrol_ads_home_parser.add_argument("--times", type=int, default=5)
    patrol_ads_home_parser.add_argument("--panel-wait", type=non_negative_float, default=0.3)
    patrol_ads_home_parser.add_argument("--ad-wait", type=non_negative_float, default=33.0)
    patrol_ads_home_parser.add_argument("--reward-wait", type=non_negative_float, default=0.5)
    patrol_ads_home_parser.add_argument("--between", type=non_negative_float, default=0.8)
    patrol_ads_home_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    patrol_ads_home_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    patrol_ads_home_parser.set_defaults(func=command_patrol_ads_from_home)

    patrol_quick_parser = sub.add_parser(
        "patrol-quick-batch",
        help="blindly run normal quick-patrol cycles without screenshots; use only after the count is verified",
    )
    patrol_quick_parser.add_argument("--times", type=int, required=True)
    patrol_quick_parser.add_argument("--reward-wait", type=non_negative_float, default=0.3)
    patrol_quick_parser.add_argument("--between", type=non_negative_float, default=0.8)
    patrol_quick_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    patrol_quick_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    patrol_quick_parser.set_defaults(func=command_patrol_quick_batch)

    mail_parser = sub.add_parser(
        "mail-claim",
        help="open top-right menu, enter mail/notice, click one-click claim, dismiss reward, and close without screenshots",
    )
    mail_parser.add_argument("--menu-wait", type=non_negative_float, default=0.3)
    mail_parser.add_argument("--open-wait", type=non_negative_float, default=0.3)
    mail_parser.add_argument("--reward-wait", type=non_negative_float, default=0.3)
    mail_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    mail_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    mail_parser.set_defaults(func=command_mail_claim)

    calendar_parser = sub.add_parser(
        "calendar-claim",
        help="open calendar, claim its visible free gift, dismiss the reward, and close",
    )
    calendar_parser.add_argument("--open-wait", type=non_negative_float, default=0.3)
    calendar_parser.add_argument("--reward-wait", type=non_negative_float, default=0.3)
    calendar_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    calendar_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    calendar_parser.set_defaults(func=command_calendar_claim)

    welfare_parser = sub.add_parser(
        "welfare-claim",
        help="open welfare, dismiss only its automatic free reward, and return without recharge tabs",
    )
    welfare_parser.add_argument("--open-wait", type=non_negative_float, default=0.3)
    welfare_parser.add_argument("--reward-wait", type=non_negative_float, default=0.3)
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

    purifier_parser = sub.add_parser(
        "journey-purifier-recruit",
        help="open Journey and recruit all available purifiers with one free click",
    )
    purifier_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    purifier_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    purifier_parser.set_defaults(func=command_journey_purifier_recruit)

    journey_daily_parser = sub.add_parser(
        "journey-daily-rewards",
        help="claim Journey resources, then complete the purifier recruit task",
    )
    _add_from_task_argument(journey_daily_parser, "journey-daily-rewards")
    journey_daily_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    journey_daily_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    journey_daily_parser.set_defaults(func=command_journey_daily_rewards)

    base_parser = sub.add_parser(
        "base-training-hall",
        help="run cafeteria, training-hall challenges, Element Trial, and play-shop purchases",
    )
    base_parser.add_argument("--battle-times", type=int, default=5)
    base_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    base_parser.add_argument("--skip-scroll", action="store_true", help="use after Computer Use has scrolled to the training hall bottom")
    _add_from_task_argument(base_parser, "base-training-hall")
    base_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    base_parser.set_defaults(func=command_base_training_hall)

    abyss_parser = sub.add_parser(
        "base-training-hall-deep-abyss",
        help="run the Deep Abyss challenge and two sweeps from the training-hall list",
    )
    abyss_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    abyss_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    abyss_parser.set_defaults(func=command_base_training_hall_deep_abyss)

    global_rescue_parser = sub.add_parser(
        "base-training-hall-global-rescue",
        help="claim the Global Rescue free reward from the training-hall list",
    )
    global_rescue_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    global_rescue_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    global_rescue_parser.set_defaults(func=command_base_training_hall_global_rescue)

    global_expedition_parser = sub.add_parser(
        "base-training-hall-global-expedition",
        help="claim the Global Expedition free reward from the training-hall list",
    )
    global_expedition_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    global_expedition_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    global_expedition_parser.set_defaults(func=command_base_training_hall_global_expedition)

    terminal_crisis_parser = sub.add_parser(
        "base-training-hall-terminal-crisis",
        help="run the Terminal Crisis free sweep from the training-hall list",
    )
    terminal_crisis_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    terminal_crisis_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    terminal_crisis_parser.set_defaults(func=command_base_training_hall_terminal_crisis)

    battlefield_contest_parser = sub.add_parser(
        "base-training-hall-battlefield-contest",
        help="run Battlefield Contest sweeps from the training-hall list",
    )
    battlefield_contest_parser.add_argument("--battle-times", type=int, default=5)
    battlefield_contest_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    battlefield_contest_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    battlefield_contest_parser.set_defaults(func=command_base_training_hall_battlefield_contest)

    element_trial_parser = sub.add_parser(
        "base-training-hall-element-trial",
        help="claim Element Trial idle reward and run one Core Trial ten-time sweep",
    )
    element_trial_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    element_trial_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    element_trial_parser.set_defaults(func=command_base_training_hall_element_trial)

    base_shop_parser = sub.add_parser(
        "base-training-hall-shop",
        help="from the training hall, purchase the enabled play-shop items at maximum quantity",
    )
    _add_from_task_argument(base_shop_parser, "base-training-hall-shop")
    base_shop_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    base_shop_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    base_shop_parser.set_defaults(func=command_base_training_hall_shop)

    shop_parser = sub.add_parser(
        "shop-training-hall",
        help="open the shop, claim the free resource gold x600, then claim special-pack gold",
    )
    _add_from_task_argument(shop_parser, "shop-training-hall")
    shop_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    shop_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    shop_parser.set_defaults(func=command_shop_training_hall)

    daily_parser = sub.add_parser(
        "daily-rewards",
        help="run all twelve daily phases with one checked game window",
    )
    daily_parser.add_argument("--fit", action=argparse.BooleanOptionalAction, default=True)
    daily_resume = daily_parser.add_mutually_exclusive_group()
    daily_resume.add_argument(
        "--from-step",
        type=int,
        choices=range(1, 9),
        default=1,
        metavar="N",
        help="legacy resume numbering: 1=patrol, 2=calendar, 3=welfare, 4=mail, 5=legion, 6=journey, 7=base training hall, 8=shop training hall",
    )
    daily_parser.add_argument("--armed-skip-animation-state", choices=("checked", "unchecked"), help="this-run Computer Use confirmation for the animation checkbox")
    daily_parser.add_argument("--armed-free-draw-state", choices=("available", "claimed"), help="this-run Computer Use confirmation for the once-daily free draw")
    daily_parser.add_argument("--armed-task-claims", type=int, help="this-run count of consecutive claimable first rows confirmed in the task list")
    daily_parser.add_argument("--mechanical-shock-skip-animation-state", choices=("checked", "unchecked"), help="机械震荡动画复选框的本次观察状态")
    daily_parser.add_argument("--mechanical-shock-task-claims", type=int, help="机械震荡本次确认当前首行可领取的连续条数，范围 0 到 3")
    daily_parser.add_argument("--mechanical-shock-mech-fight-claim-state", choices=("available", "claimed"), help="机甲械斗页一键领取状态的本次观察")
    daily_parser.add_argument("--pass-free-claim-state", choices=("available", "claimed"), help="通行证绿色一键领取状态的本次页面观察")
    daily_parser.add_argument("--pass-work-plan-sign-state", choices=("available", "claimed"), help="当天作战计划直免签到状态的本次页面观察")
    daily_parser.add_argument("--mimic-skip-animation-state", choices=("checked", "unchecked"), help="拟态牌库动画复选框的本次观察状态")
    daily_parser.add_argument("--mimic-free-draw-state", choices=("available", "claimed"), help="拟态牌库每日免费抽取的本次观察状态")
    daily_parser.add_argument("--mimic-task-claims", type=int, help="拟态牌库本次确认当前首行可领取的连续条数")
    daily_parser.add_argument("--mimic-one-click-claim-state", choices=("available", "claimed"), help="拟态牌库红点页一键奖励的本次观察状态")
    daily_resume.add_argument(
        "--from-task",
        choices=DAILY_TASK_IDS,
        metavar="TASK",
        help=(
            "resume at a named business task and continue later tasks and phases; "
            f"required entry pages by ID: {task_entry_help('daily-rewards')}"
        ),
    )
    daily_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    daily_parser.add_argument("--dry-run", action="store_true", help="print planned task flows without clicking or sleeping")
    daily_parser.set_defaults(func=command_daily_rewards)

    legion_daily_parser = sub.add_parser(
        "legion-daily-rewards",
        help="run daily cut, foreign rewards, Legion shop purchases, and Journey gifts",
    )
    legion_daily_parser.add_argument("--sweep-times", type=int, default=2)
    legion_daily_parser.add_argument("--confirm-wait", type=non_negative_float, default=0.3)
    legion_daily_parser.add_argument("--sweep-reward-wait", type=non_negative_float, default=0.3)
    legion_daily_parser.add_argument("--sweep-between", type=non_negative_float, default=0.3)
    legion_daily_parser.add_argument("--reward-page-wait", type=non_negative_float, default=0.3)
    legion_daily_parser.add_argument("--reward-wait", type=non_negative_float, default=0.3)
    _add_from_task_argument(legion_daily_parser, "legion-daily-rewards")
    legion_daily_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    legion_daily_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    legion_daily_parser.set_defaults(func=command_legion_daily_rewards)

    legion_reward_parser = sub.add_parser(
        "legion-reward-claims",
        help="run foreign-challenge sweeps and claim the first legion and personal reward entries",
    )
    legion_reward_parser.add_argument("--sweep-times", type=int, default=2)
    legion_reward_parser.add_argument("--confirm-wait", type=non_negative_float, default=0.3)
    legion_reward_parser.add_argument("--sweep-reward-wait", type=non_negative_float, default=0.3)
    legion_reward_parser.add_argument("--sweep-between", type=non_negative_float, default=0.3)
    legion_reward_parser.add_argument("--reward-page-wait", type=non_negative_float, default=0.3)
    legion_reward_parser.add_argument("--reward-wait", type=non_negative_float, default=0.3)
    _add_from_task_argument(legion_reward_parser, "legion-reward-claims")
    legion_reward_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    legion_reward_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    legion_reward_parser.set_defaults(func=command_legion_reward_claims)

    legion_sweep_parser = sub.add_parser(
        "legion-sweep-batch",
        help="run verified foreign-challenge sweep cycles without screenshots between cycles",
    )
    legion_sweep_parser.add_argument("--times", type=int, required=True)
    legion_sweep_parser.add_argument("--confirm-wait", type=non_negative_float, default=0.3)
    legion_sweep_parser.add_argument("--reward-wait", type=non_negative_float, default=0.3)
    legion_sweep_parser.add_argument("--between", type=non_negative_float, default=0.3)
    legion_sweep_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    legion_sweep_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    legion_sweep_parser.set_defaults(func=command_legion_sweep_batch)

    legion_gifts_parser = sub.add_parser("legion-journey-gifts", help="claim expedition gifts and perform three 40-energy search sweeps")
    _add_from_task_argument(legion_gifts_parser, "legion-journey-gifts")
    legion_gifts_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    legion_gifts_parser.add_argument("--dry-run", action="store_true")
    legion_gifts_parser.set_defaults(func=command_legion_journey_gifts)

    legion_shop_parser = sub.add_parser(
        "legion-shop-purchases",
        help="open the legion shop and scroll its purchase list to the bottom",
    )
    _add_from_task_argument(legion_shop_parser, "legion-shop-purchases")
    legion_shop_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    legion_shop_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    legion_shop_parser.set_defaults(func=command_legion_shop_purchases)

    test_parser = sub.add_parser("self-test", help="run non-clicking internal checks")
    test_parser.set_defaults(func=command_self_test)

    return parser


def command_requires_focus(args: argparse.Namespace | str) -> bool:
    """判断命令是否需要聚焦游戏窗口；只读命令和模拟坐标预演免于聚焦。"""
    if isinstance(args, str):
        return args not in NON_OPERATING_COMMANDS
    if args.command in NON_OPERATING_COMMANDS:
        return False
    return not (bool(getattr(args, "mock_bounds", None)) and bool(getattr(args, "dry_run", False)))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    session_started = False
    try:
        if (
            getattr(args, "mock_bounds", None)
            and not getattr(args, "dry_run", False)
            and args.command not in {"bounds", "dry-run", "list", "state", "self-test"}
        ):
            raise ClickError("--mock-bounds is simulation-only; add --dry-run instead of executing clicks")
        if command_requires_focus(args):
            start_input_session()
            session_started = True
            focus_game_window_at_start()
        return args.func(args)
    except ClickError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        if session_started:
            end_input_session()


if __name__ == "__main__":
    raise SystemExit(main())
