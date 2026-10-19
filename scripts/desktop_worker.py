#!/usr/bin/env python3
"""向僵尸开炮桌面 App 的结构化任务执行入口。"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import signal
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import zombie_click as cli
from scripts import zombie_common as common
from scripts.zombie_tasks.resume import (
    DAILY_TASK_ENTRY_PAGES,
    DAILY_TASK_IDS,
    DAILY_TASK_TARGETS,
    LOCAL_TASK_ENTRY_PAGES,
)


MOCK_BOUNDS = "2,33,508,949"
DAILY_PHASE_ORDER = ("patrol", "mechanical_shock", "battle_pass", "armed_descent", "mimic_card_library", "calendar", "welfare", "mail", "legion", "journey", "base", "shop")
DAILY_PHASE_COMMANDS = {
    "patrol": "patrol-full-from-home",
    "mechanical_shock": "mechanical-shock",
    "battle_pass": "battle-pass-daily",
    "armed_descent": "armed-descent",
    "mimic_card_library": "mimic-card-library",
    "calendar": "calendar-claim",
    "welfare": "welfare-claim",
    "mail": "mail-claim",
    "legion": "legion-daily-rewards",
    "journey": "journey-daily-rewards",
    "base": "base-training-hall",
    "shop": "shop-training-hall",
}

_TASK_NAMES = {
    "patrol.claim": "领取巡逻收益",
    "patrol.quick_patrol": "普通快速巡逻",
    "patrol.ad_patrol": "广告快速巡逻",
    "mechanical.shock": "机械震荡",
    "pass.daily": "通行证与作战计划签到",
    "armed.descent": "武装降临",
    "mimic.card_library": "拟态牌库",
    "calendar": "日历礼包",
    "welfare": "福利免费奖励",
    "mail": "邮件奖励",
    "legion.daily_cut": "军团每日一刀",
    "legion.foreign_rewards": "军团异域挑战奖励",
    "legion.shop_purchases": "军团商店采购",
    "legion.journey_gifts": "军团征途礼物",
    "journey.resources": "征途资源",
    "journey.purifier": "净化者招募",
    "base.cafeteria": "基地食堂",
    "base.global_rescue": "寰球救援",
    "base.global_expedition": "寰球远征",
    "base.deep_abyss": "深渊挑战",
    "base.terminal_crisis": "末日危机",
    "base.battlefield_contest": "巅峰争霸",
    "base.element_trial": "元素试炼",
    "base.play_shop": "玩法商店采购",
    "shop.resource_gold": "商城资源金币",
    "shop.special_pack_gold": "特惠礼包金币",
}

_DAILY_TASK_ROUTES = {
    "patrol.claim": ("首页", "巡逻"), "patrol.quick_patrol": ("首页", "巡逻"), "patrol.ad_patrol": ("首页", "巡逻"),
    "mechanical.shock": ("首页", "机械震荡"), "pass.daily": ("首页", "通行证"),
    "armed.descent": ("首页", "武装降临"), "mimic.card_library": ("首页", "拟态牌库"),
    "calendar": ("首页", "日历礼包"), "welfare": ("首页", "福利"), "mail": ("首页", "邮件"),
    "legion.daily_cut": ("军团", "每日一刀"), "legion.foreign_rewards": ("军团", "异域挑战"),
    "legion.shop_purchases": ("军团", "军团商店"), "legion.journey_gifts": ("军团", "征途礼物"),
    "journey.resources": ("征途", "征途地图"), "journey.purifier": ("征途", "净化者"),
    "base.cafeteria": ("基地", "基地食堂"), "base.global_rescue": ("基地", "历练大厅"),
    "base.global_expedition": ("基地", "历练大厅"), "base.deep_abyss": ("基地", "历练大厅"),
    "base.terminal_crisis": ("基地", "历练大厅"), "base.battlefield_contest": ("基地", "历练大厅"),
    "base.element_trial": ("基地", "历练大厅"), "base.play_shop": ("基地", "玩法商店"),
    "shop.resource_gold": ("商城", "资源"), "shop.special_pack_gold": ("商城", "特惠礼包"),
}

_SHARED_ARGUMENT_KEYS = {
    "daily-rewards": {
        "fit": "window.fit", "armed_skip_animation_state": "armed.skip_animation_state",
        "armed_free_draw_state": "armed.free_draw_state", "armed_task_claims": "armed.task_claims",
        "mechanical_shock_skip_animation_state": "mechanical_shock.skip_animation_state",
        "mechanical_shock_task_claims": "mechanical_shock.task_claims",
        "mechanical_shock_mech_fight_claim_state": "mechanical_shock.mech_fight_claim_state",
        "pass_free_claim_state": "battle_pass.free_claim_state", "pass_work_plan_sign_state": "battle_pass.work_plan_sign_state",
        "mimic_skip_animation_state": "mimic.skip_animation_state", "mimic_free_draw_state": "mimic.free_draw_state",
        "mimic_task_claims": "mimic.task_claims", "mimic_one_click_claim_state": "mimic.one_click_claim_state",
    },
    "armed-descent": {"skip_animation_state": "armed.skip_animation_state", "free_draw_state": "armed.free_draw_state", "task_claims": "armed.task_claims"},
    "mechanical-shock": {"mechanical_shock_skip_animation_state": "mechanical_shock.skip_animation_state", "mechanical_shock_task_claims": "mechanical_shock.task_claims", "mechanical_shock_mech_fight_claim_state": "mechanical_shock.mech_fight_claim_state"},
    "battle-pass-daily": {"free_claim_state": "battle_pass.free_claim_state", "work_plan_sign_state": "battle_pass.work_plan_sign_state"},
    "mimic-card-library": {"mimic_skip_animation_state": "mimic.skip_animation_state", "mimic_free_draw_state": "mimic.free_draw_state", "mimic_task_claims": "mimic.task_claims", "mimic_one_click_claim_state": "mimic.one_click_claim_state"},
    "patrol-full-from-home": {"quick_times": "patrol.quick_times", "ad_times": "patrol.ad_times", "panel_wait": "patrol.panel_wait", "claim_wait": "patrol.claim_wait", "dismiss_wait": "patrol.dismiss_wait", "quick_reward_wait": "patrol.quick_reward_wait", "quick_between": "patrol.quick_between", "ad_wait": "patrol.ad_wait", "ad_close_wait": "patrol.ad_close_wait", "ad_reward_wait": "patrol.ad_reward_wait", "ad_between": "patrol.ad_between", "close_wait": "patrol.close_wait", "fit": "window.fit"},
    "patrol-quick-batch": {"times": "patrol.quick_times", "reward_wait": "patrol.quick_reward_wait", "between": "patrol.quick_between"},
    "patrol-ads-batch": {"times": "patrol.ad_times", "ad_wait": "patrol.ad_wait", "reward_wait": "patrol.ad_reward_wait", "between": "patrol.ad_between"},
    "patrol-ads-from-home": {"times": "patrol.ad_times", "panel_wait": "patrol.panel_wait", "ad_wait": "patrol.ad_wait", "reward_wait": "patrol.ad_reward_wait", "between": "patrol.ad_between"},
    "legion-daily-rewards": {"sweep_times": "legion.sweep_times", "confirm_wait": "legion.confirm_wait", "sweep_reward_wait": "legion.sweep_reward_wait", "sweep_between": "legion.sweep_between", "reward_page_wait": "legion.reward_page_wait", "reward_wait": "legion.reward_wait"},
    "legion-reward-claims": {"sweep_times": "legion.sweep_times", "confirm_wait": "legion.confirm_wait", "sweep_reward_wait": "legion.sweep_reward_wait", "sweep_between": "legion.sweep_between", "reward_page_wait": "legion.reward_page_wait", "reward_wait": "legion.reward_wait"},
    "legion-sweep-batch": {"times": "legion.sweep_times", "confirm_wait": "legion.confirm_wait", "reward_wait": "legion.sweep_reward_wait", "between": "legion.sweep_between"},
    "base-training-hall": {"battle_times": "base.battle_times", "skip_scroll": "base.skip_scroll"},
    "base-training-hall-battlefield-contest": {"battle_times": "base.battle_times"},
}


def _shared_argument_key(command_id: str, argument_name: str) -> str | None:
    if argument_name == "backend":
        return "input.backend"
    return _SHARED_ARGUMENT_KEYS.get(command_id, {}).get(argument_name)

_COMMANDS = {
    "battle-pass-daily": ("通行证每日免费奖励", "首页"),
    "armed-descent": ("武装降临", "首页"),
    "mimic-card-library": ("拟态牌库", "首页"),
    "mechanical-shock": ("机械震荡每日奖励", "首页"),
    "patrol-ads-batch": ("广告快速巡逻批次", "巡逻面板"),
    "patrol-full-from-home": ("完整巡逻任务", "首页"),
    "patrol-ads-from-home": ("首页广告巡逻", "首页"),
    "patrol-quick-batch": ("普通快速巡逻批次", "巡逻面板"),
    "mail-claim": ("邮件奖励", "首页"),
    "calendar-claim": ("日历礼包", "首页"),
    "welfare-claim": ("福利免费奖励", "首页"),
    "journey-resource-claim": ("征途资源", "首页"),
    "journey-purifier-recruit": ("净化者招募", "首页"),
    "journey-daily-rewards": ("征途每日任务", "首页"),
    "base-training-hall": ("基地与训练大厅任务", "首页"),
    "base-training-hall-deep-abyss": ("深渊挑战", "训练大厅列表"),
    "base-training-hall-global-rescue": ("寰球救援", "训练大厅列表"),
    "base-training-hall-global-expedition": ("寰球远征", "训练大厅列表"),
    "base-training-hall-terminal-crisis": ("末日危机", "训练大厅列表"),
    "base-training-hall-battlefield-contest": ("巅峰争霸", "训练大厅列表"),
    "base-training-hall-element-trial": ("元素试炼", "训练大厅列表"),
    "base-training-hall-shop": ("玩法商店采购", "训练大厅列表"),
    "daily-rewards": ("完整每日任务", "首页"),
    "legion-daily-rewards": ("军团每日任务", "首页"),
    "legion-reward-claims": ("军团挑战领奖", "首页"),
    "legion-sweep-batch": ("军团扫荡批次", "异域挑战页"),
    "legion-journey-gifts": ("军团征途礼物", "军团页"),
    "legion-shop-purchases": ("军团商店采购", "军团页"),
    "shop-training-hall": ("商城免费金币", "首页"),
}

_COMMAND_CATEGORIES = {
    "daily-rewards": "daily",
    "battle-pass-daily": "rewards",
    "armed-descent": "rewards",
    "mimic-card-library": "rewards",
    "mechanical-shock": "rewards",
    "patrol-ads-batch": "patrol",
    "patrol-full-from-home": "patrol",
    "patrol-ads-from-home": "patrol",
    "patrol-quick-batch": "patrol",
    "mail-claim": "rewards",
    "calendar-claim": "rewards",
    "welfare-claim": "rewards",
    "legion-daily-rewards": "legion",
    "legion-reward-claims": "legion",
    "legion-sweep-batch": "legion",
    "legion-journey-gifts": "legion",
    "legion-shop-purchases": "legion",
    "journey-resource-claim": "journey",
    "journey-purifier-recruit": "journey",
    "journey-daily-rewards": "journey",
    "base-training-hall": "base",
    "base-training-hall-deep-abyss": "base",
    "base-training-hall-global-rescue": "base",
    "base-training-hall-global-expedition": "base",
    "base-training-hall-terminal-crisis": "base",
    "base-training-hall-battlefield-contest": "base",
    "base-training-hall-element-trial": "base",
    "base-training-hall-shop": "base",
    "shop-training-hall": "shop",
}


class WorkerError(ValueError):
    """桌面协议或任务选择不符合支持范围。"""


class WorkerCancelled(RuntimeError):
    """桌面 App 已请求停止当前任务。"""


@dataclass(frozen=True)
class DailyPhase:
    id: str
    task_ids: tuple[str, ...]
    local_task_ids: tuple[str, ...]
    entry_page: str


class CancellationToken:
    """接收停止信号，并在两次物理输入之间结束任务。"""

    def __init__(self) -> None:
        self._event = threading.Event()

    def request_stop(self) -> None:
        self._event.set()

    @property
    def stopped(self) -> bool:
        return self._event.is_set()

    def check(self) -> None:
        if self.stopped:
            raise WorkerCancelled("用户已停止任务")

    def wait(self, seconds: float) -> None:
        self.check()
        if seconds > 0 and self._event.wait(seconds):
            raise WorkerCancelled("用户已停止任务")
        self.check()


def _daily_phase_id(task_id: str) -> str:
    try:
        return DAILY_TASK_TARGETS[task_id][0]
    except KeyError as exc:
        raise WorkerError(f"未知每日任务 ID：{task_id}") from exc


def build_daily_plan(task_ids: Sequence[str], from_task: str | None = None) -> tuple[DailyPhase, ...]:
    """按既有每日阶段顺序筛选启用任务，并截取所选起点之后的后缀。"""
    if isinstance(task_ids, (str, bytes)) or not isinstance(task_ids, Sequence):
        raise WorkerError("task_ids 必须是任务 ID 数组")
    selected = list(task_ids)
    if not selected:
        raise WorkerError("至少启用一个每日任务")
    if any(not isinstance(task_id, str) for task_id in selected):
        raise WorkerError("每日任务 ID 必须是字符串")
    if len(set(selected)) != len(selected):
        raise WorkerError("每日任务 ID 不能重复")
    unknown = [task_id for task_id in selected if task_id not in DAILY_TASK_IDS]
    if unknown:
        raise WorkerError(f"未知每日任务 ID：{', '.join(unknown)}")
    if from_task is not None:
        if not isinstance(from_task, str) or from_task not in selected:
            raise WorkerError("起始任务必须是已启用的每日任务")
        first_index = DAILY_TASK_IDS.index(from_task)
    else:
        first_index = 0
    enabled_suffix = tuple(
        task_id
        for task_id in DAILY_TASK_IDS[first_index:]
        if task_id in set(selected)
    )
    if not enabled_suffix:
        raise WorkerError("所选起点之后没有启用任务")

    phases: list[DailyPhase] = []
    for phase_id in DAILY_PHASE_ORDER:
        ids = tuple(task_id for task_id in enabled_suffix if _daily_phase_id(task_id) == phase_id)
        if not ids:
            continue
        # 三个单步首页任务不经过复合处理器，因此以全局 ID 作为其回调键。
        local_ids = tuple(DAILY_TASK_TARGETS[task_id][1] or task_id for task_id in ids)
        phases.append(DailyPhase(phase_id, ids, local_ids, DAILY_TASK_ENTRY_PAGES[ids[0]]))
    return tuple(phases)


def _emit_task_event(
    emit: Callable[[dict[str, object]], None], task_id: str, status: str
) -> None:
    if status == "started":
        emit({"type": "task_started", "task_id": task_id})
    else:
        emit({"type": "task_finished", "task_id": task_id, "status": status})


def execute_daily_plan(
    plan: Sequence[DailyPhase],
    run_phase: Callable[[DailyPhase, Callable[[str, str], None]], None],
    emit: Callable[[dict[str, object]], None],
    *,
    dry_run: bool = False,
    emit_run_finished: bool = True,
) -> str:
    """逐阶段运行计划；任何失败或停止都阻断后续阶段。"""
    active_task: str | None = None
    skipped_task = False
    known_tasks = {task_id for phase in plan for task_id in phase.task_ids}

    def report_task(task_id: str, status: str) -> None:
        nonlocal active_task, skipped_task
        if task_id not in known_tasks:
            raise WorkerError(f"阶段返回了计划外任务：{task_id}")
        if status == "started":
            if active_task is not None:
                raise WorkerError(f"任务 {active_task} 尚未结束，不能启动 {task_id}")
            active_task = task_id
            _emit_task_event(emit, task_id, "started")
            return
        if status not in {"completed", "skipped", "failed", "stopped"}:
            raise WorkerError(f"未知任务状态：{status}")
        if active_task != task_id:
            raise WorkerError(f"结束任务与当前任务不一致：{task_id}")
        _emit_task_event(emit, task_id, "completed" if status == "completed" else status)
        if status == "skipped":
            skipped_task = True
        active_task = None
        if status == "failed":
            raise WorkerError(f"任务 {task_id} 报告失败")
        if status == "stopped":
            raise WorkerCancelled(f"任务 {task_id} 已停止")

    try:
        for phase in plan:
            run_phase(phase, report_task)
            if active_task is not None:
                raise WorkerError(f"阶段 {phase.id} 未结束当前任务 {active_task}")
    except WorkerCancelled as exc:
        if active_task is not None:
            _emit_task_event(emit, active_task, "stopped")
        emit({"type": "log", "message": str(exc)})
        if emit_run_finished:
            emit({"type": "run_finished", "status": "stopped"})
        return "stopped"
    except Exception as exc:
        if active_task is not None:
            _emit_task_event(emit, active_task, "failed")
        emit({"type": "error", "message": str(exc) or exc.__class__.__name__})
        if emit_run_finished:
            emit({"type": "run_finished", "status": "failed"})
        return "failed"
    status = "partial" if skipped_task else ("dry_run_completed" if dry_run else "completed")
    if emit_run_finished:
        emit({"type": "run_finished", "status": status})
    return status


def _arg_type(action: argparse.Action) -> str:
    if isinstance(action, argparse.BooleanOptionalAction) or isinstance(
        action, (argparse._StoreTrueAction, argparse._StoreFalseAction)
    ):
        return "boolean"
    if action.choices is not None:
        return "choice"
    parser_type_name = getattr(action.type, "__name__", "")
    if action.type is int or "int" in parser_type_name:
        return "integer"
    if action.type is float or "float" in parser_type_name:
        return "number"
    return "string"


def _command_argument_metadata(parser: argparse.ArgumentParser) -> list[dict[str, object]]:
    fields: list[dict[str, object]] = []
    position = 0
    for action in parser._actions:
        if action.dest in {"help", "func"} or isinstance(action, argparse._HelpAction):
            continue
        if action.dest == "dry_run":
            continue
        is_option = bool(action.option_strings)
        field: dict[str, object] = {
            "name": action.dest,
            "type": _arg_type(action),
            "default": action.default,
            "required": bool(action.required or (not is_option and action.nargs not in ("?", "*"))),
            "flag": action.option_strings[0] if is_option else None,
            "position": None if is_option else position,
        }
        shared_key = _shared_argument_key(parser.prog.rsplit(" ", 1)[-1], action.dest)
        if shared_key:
            field["shared_key"] = shared_key
        choices = set(action.choices or ())
        if {"available", "claimed"} <= choices:
            field["default"] = "available"
        elif {"checked", "unchecked"} <= choices:
            field["default"] = "checked"
        elif action.dest.endswith("task_claims"):
            field["default"] = 3
        if not is_option:
            position += 1
        if action.choices is not None:
            field["choices"] = list(action.choices)
        negatives = [flag for flag in action.option_strings if flag.startswith("--no-")]
        if negatives:
            field["negative_flag"] = negatives[0]
        fields.append(field)
    return fields


def _normalize_shared_metadata(commands: list[dict[str, object]]) -> None:
    """让同一共享参数在所有命令表单中呈现同一个默认值和必填规则。"""
    by_id = {str(command["id"]): command for command in commands}
    canonical_ids = ["daily-rewards", *(DAILY_PHASE_COMMANDS[phase] for phase in DAILY_PHASE_ORDER)]
    canonical: dict[str, dict[str, object]] = {}
    for command_id in canonical_ids:
        command = by_id.get(command_id)
        if not command:
            continue
        for argument in command["args"]:
            key = argument.get("shared_key")
            if key and key not in canonical:
                canonical[str(key)] = argument
    for command in commands:
        for argument in command["args"]:
            source = canonical.get(str(argument.get("shared_key")))
            if source:
                argument["default"] = source.get("default")
                argument["required"] = source.get("required", False)
                if source.get("choices") is not None:
                    argument["choices"] = list(source["choices"])


def build_catalog() -> dict[str, object]:
    """导出唯一任务目录与命令参数定义，供桌面界面生成表单。"""
    parser = cli.build_parser()
    subparsers = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))
    help_by_command = {action.dest: action.help for action in subparsers._choices_actions}
    commands = []
    for command_id, (name, entry_page) in _COMMANDS.items():
        command_parser = subparsers.choices[command_id]
        argument_metadata = _command_argument_metadata(command_parser)
        command = {
            "id": command_id,
            "name": name,
            "category": _COMMAND_CATEGORIES.get(command_id, "other"),
            "description": command_parser.description or help_by_command.get(command_id) or name,
            "entry_page": entry_page,
            "args": argument_metadata,
        }
        if any(argument["name"] == "from_task" for argument in argument_metadata):
            entry_pages = (
                DAILY_TASK_ENTRY_PAGES
                if command_id == "daily-rewards"
                else LOCAL_TASK_ENTRY_PAGES.get(command_id)
            )
            if entry_pages:
                command["entry_pages"] = dict(entry_pages)
        commands.append(command)
    _normalize_shared_metadata(commands)
    # 命令列表遵循每日任务首次出现的业务顺序，别名紧跟对应操作，便于对照修改。
    display_order = [
        "daily-rewards", "patrol-full-from-home", "patrol-quick-batch", "patrol-ads-batch", "patrol-ads-from-home",
        "mechanical-shock", "battle-pass-daily", "armed-descent", "mimic-card-library", "calendar-claim", "welfare-claim", "mail-claim",
        "legion-daily-rewards", "legion-reward-claims", "legion-sweep-batch", "legion-shop-purchases", "legion-journey-gifts",
        "journey-daily-rewards", "journey-resource-claim", "journey-purifier-recruit",
        "base-training-hall", "base-training-hall-global-rescue", "base-training-hall-global-expedition", "base-training-hall-deep-abyss",
        "base-training-hall-terminal-crisis", "base-training-hall-battlefield-contest", "base-training-hall-element-trial", "base-training-hall-shop",
        "shop-training-hall",
    ]
    command_positions = {command_id: index for index, command_id in enumerate(display_order)}
    commands.sort(key=lambda command: command_positions.get(str(command["id"]), len(display_order)))
    daily_tasks = [
        {
            "id": task_id,
            "name": _TASK_NAMES[task_id],
            "entry_page": DAILY_TASK_ENTRY_PAGES[task_id],
            "phase": _daily_phase_id(task_id),
            "tab": _DAILY_TASK_ROUTES[task_id][0],
            "module": _DAILY_TASK_ROUTES[task_id][1],
        }
        for task_id in DAILY_TASK_IDS
    ]
    return {"commands": commands, "daily_tasks": daily_tasks}


def parse_command_args(command: str, args: Sequence[str], *, dry_run: bool) -> argparse.Namespace:
    """使用现有 argparse 定义校验命令和参数，不拼接或执行 shell 文本。"""
    if command not in _COMMANDS:
        raise WorkerError(f"不支持的命令：{command}")
    if isinstance(args, (str, bytes)) or not isinstance(args, Sequence) or any(
        not isinstance(value, str) for value in args
    ):
        raise WorkerError("args 必须是字符串数组")
    if any(value in {"--dry-run", "--mock-bounds", "--json", "-h", "--help"} for value in args):
        raise WorkerError("dry-run、mock-bounds、json 和 help 参数由桌面执行器管理")
    argv = ["--mock-bounds", MOCK_BOUNDS] if dry_run else []
    argv.extend((command, *args))
    if dry_run:
        argv.append("--dry-run")
    parser = cli.build_parser()
    error_output = io.StringIO()
    try:
        with contextlib.redirect_stderr(error_output):
            parsed = parser.parse_args(argv)
    except SystemExit as exc:
        detail = error_output.getvalue().strip().splitlines()
        raise WorkerError(detail[-1] if detail else "命令参数无效") from exc
    return parsed


def _explicit_argument_destinations(command: str, arguments: Sequence[str]) -> set[str]:
    """识别 argv 中显式填写的参数，避免 parser 默认状态覆盖本次确认值。"""
    parser = cli.build_parser()
    subparsers = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))
    command_parser = subparsers.choices[command]
    explicit: set[str] = set()
    for action in command_parser._actions:
        if any(
            token == option or token.startswith(f"{option}=")
            for token in arguments
            for option in action.option_strings
        ):
            explicit.add(action.dest)
    return explicit


def _phase_args(
    phase: DailyPhase,
    bounds: common.Bounds,
    *,
    backend: str,
    dry_run: bool,
    explicit_from_task: str | None,
    has_previous_task: bool,
    task_event: Callable[[str, str], None],
    phase_arguments: Sequence[str] = (),
    explicit_phase_arguments: set[str] | None = None,
    pass_gate_values: tuple[str | None, str | None] = (None, None),
    armed_gate_values: tuple[str | None, str | None, int | None] = (None, None, None),
    mechanical_shock_gate_values: tuple[str | None, int | None, str | None] = (None, None, None),
    mimic_gate_values: tuple[str | None, str | None, int | None, str | None] = (None, None, None, None),
) -> argparse.Namespace:
    command_id = DAILY_PHASE_COMMANDS[phase.id]
    args = parse_command_args(command_id, phase_arguments, dry_run=dry_run)
    args.mock_bounds = bounds
    args.fit = False
    if not phase_arguments:
        args.backend = backend
    args.dry_run = dry_run
    args.desktop_task_ids = phase.local_task_ids
    args.desktop_task_event = task_event
    args.from_task = phase.local_task_ids[0] if len(phase.local_task_ids) and (
        phase.local_task_ids[0] != _phase_first_task(phase.id) or explicit_from_task is not None
    ) else None
    explicit_phase_arguments = explicit_phase_arguments or set()

    def prefer_gate(argument_name: str, daily_value: object) -> object:
        # 优先级：阶段单命令显式值，其次完整日常显式 gate，最后才用参数目录默认值。
        if argument_name in explicit_phase_arguments or daily_value is None:
            return getattr(args, argument_name)
        return daily_value

    if phase.id == "battle_pass":
        args.free_claim_state = prefer_gate("free_claim_state", pass_gate_values[0])
        args.work_plan_sign_state = prefer_gate("work_plan_sign_state", pass_gate_values[1])
    elif phase.id == "armed_descent":
        args.skip_animation_state = prefer_gate("skip_animation_state", armed_gate_values[0])
        args.free_draw_state = prefer_gate("free_draw_state", armed_gate_values[1])
        args.task_claims = prefer_gate("task_claims", armed_gate_values[2])
    elif phase.id == "mechanical_shock":
        args.mechanical_shock_skip_animation_state = prefer_gate("mechanical_shock_skip_animation_state", mechanical_shock_gate_values[0])
        args.mechanical_shock_task_claims = prefer_gate("mechanical_shock_task_claims", mechanical_shock_gate_values[1])
        args.mechanical_shock_mech_fight_claim_state = prefer_gate("mechanical_shock_mech_fight_claim_state", mechanical_shock_gate_values[2])
    elif phase.id == "mimic_card_library":
        args.mimic_skip_animation_state = prefer_gate("mimic_skip_animation_state", mimic_gate_values[0])
        args.mimic_free_draw_state = prefer_gate("mimic_free_draw_state", mimic_gate_values[1])
        args.mimic_task_claims = prefer_gate("mimic_task_claims", mimic_gate_values[2])
        args.mimic_one_click_claim_state = prefer_gate("mimic_one_click_claim_state", mimic_gate_values[3])
    first_local = phase.local_task_ids[0]
    if phase.id == "legion" and first_local in {"shop", "journey_gifts"} and has_previous_task:
        args.desktop_navigate_legion = True
    if phase.id == "base" and has_previous_task:
        args.desktop_navigate_base = True
        args.desktop_navigate_training_hall = first_local != "cafeteria"
    if phase.id == "shop" and first_local == "special_pack_gold" and has_previous_task:
        args.desktop_navigate_shop_special = True
    return args


def _phase_first_task(phase_id: str) -> str:
    return {
        "patrol": "claim",
        "mechanical_shock": "mechanical.shock",
        "battle_pass": "pass.daily",
        "armed_descent": "armed.descent",
        "mimic_card_library": "mimic.card_library",
        "calendar": "calendar",
        "welfare": "welfare",
        "mail": "mail",
        "legion": "daily_cut",
        "journey": "resources",
        "base": "cafeteria",
        "shop": "resource_gold",
    }[phase_id]


def _preflight_live(*, fit: bool, token: CancellationToken | None = None) -> common.Bounds:
    """执行前确认 macOS 游戏窗口并锁定本次任务使用的校准边界。"""
    if token is not None:
        token.check()
    if sys.platform != "darwin":
        raise WorkerError("Windows 暂未实现游戏窗口和输入后端；当前只能运行模拟任务。")
    common.start_input_session()
    common.focus_game_window_at_start()
    if token is not None:
        token.check()
    bounds = common.fit_game_window() if fit else common.ensure_valid_game_bounds(common.front_window_bounds())
    common.validate_bounds(bounds, allow_mock=False)
    common.bind_input_session(bounds)
    return bounds


def _install_cancellation(token: CancellationToken) -> tuple[Callable[..., object], Callable[..., object]]:
    """在每次点击、拖动和可取消等待前检查桌面停止请求。"""
    original_check = common._cancel_check
    original_wait = common._cancel_wait
    common.configure_cancellation(token.check, token.wait)
    return original_check, original_wait


def _restore_cancellation(previous: tuple[Callable[..., object], Callable[..., object]]) -> None:
    common.configure_cancellation(*previous)


def _run_daily_phase(
    phase: DailyPhase,
    task_event: Callable[[str, str], None],
    *,
    bounds: common.Bounds,
    backend: str,
    dry_run: bool,
    explicit_from_task: str | None,
    has_previous_task: bool,
    phase_arguments: Sequence[str] = (),
    explicit_phase_arguments: set[str] | None = None,
    pass_gate_values: tuple[str | None, str | None] = (None, None),
    armed_gate_values: tuple[str | None, str | None, int | None] = (None, None, None),
    mechanical_shock_gate_values: tuple[str | None, int | None, str | None] = (None, None, None),
    mimic_gate_values: tuple[str | None, str | None, int | None, str | None] = (None, None, None, None),
) -> None:
    args = _phase_args(
        phase,
        bounds,
        backend=backend,
        dry_run=dry_run,
        explicit_from_task=explicit_from_task,
        has_previous_task=has_previous_task,
        task_event=task_event,
        phase_arguments=phase_arguments,
        explicit_phase_arguments=explicit_phase_arguments,
        pass_gate_values=pass_gate_values,
        armed_gate_values=armed_gate_values,
        mechanical_shock_gate_values=mechanical_shock_gate_values,
        mimic_gate_values=mimic_gate_values,
    )
    result = args.func(args)
    if result not in (None, 0):
        raise WorkerError(f"阶段 {phase.id} 返回失败状态：{result}")


def _call_phase_with_events(
    phase: DailyPhase,
    report_task: Callable[[str, str], None],
    *,
    bounds: common.Bounds,
    backend: str,
    dry_run: bool,
    explicit_from_task: str | None,
    has_previous_task: bool,
    phase_arguments: Sequence[str] = (),
    explicit_phase_arguments: set[str] | None = None,
    pass_gate_values: tuple[str | None, str | None] = (None, None),
    armed_gate_values: tuple[str | None, str | None, int | None] = (None, None, None),
    mechanical_shock_gate_values: tuple[str | None, int | None, str | None] = (None, None, None),
    mimic_gate_values: tuple[str | None, str | None, int | None, str | None] = (None, None, None, None),
) -> None:
    local_to_global = dict(zip(phase.local_task_ids, phase.task_ids))

    def report_local(local_id: str, status: str) -> None:
        if local_id not in local_to_global:
            raise WorkerError(f"阶段 {phase.id} 返回未知子任务：{local_id}")
        report_task(local_to_global[local_id], status)

    # 日历、福利和邮件没有复合任务回调，由执行器在单一处理器外补齐事件。
    single_handler_task = phase.local_task_ids[0] if phase.id in {"calendar", "welfare", "mail"} else None
    if single_handler_task is not None:
        report_local(single_handler_task, "started")
    _run_daily_phase(
        phase,
        report_local,
        bounds=bounds,
        backend=backend,
        dry_run=dry_run,
        explicit_from_task=explicit_from_task,
        has_previous_task=has_previous_task,
        phase_arguments=phase_arguments,
        explicit_phase_arguments=explicit_phase_arguments,
        pass_gate_values=pass_gate_values,
        armed_gate_values=armed_gate_values,
        mechanical_shock_gate_values=mechanical_shock_gate_values,
        mimic_gate_values=mimic_gate_values,
    )
    if single_handler_task is not None:
        report_local(single_handler_task, "completed")


def _run_single_command(
    command: str,
    args: argparse.Namespace,
    emit: Callable[[dict[str, object]], None],
    token: CancellationToken,
    *,
    emit_run_finished: bool = True,
) -> str:
    """运行一个目录中登记的现有命令，并将其完整输出转为日志事件。"""
    task_id = command
    emit({"type": "task_started", "task_id": task_id})
    try:
        if args.dry_run:
            bounds = args.mock_bounds
        else:
            bounds = _preflight_live(fit=bool(getattr(args, "fit", False)), token=token)
        if bounds is not None and not args.dry_run:
            args.mock_bounds = bounds
        result = args.func(args)
        if result not in (None, 0):
            raise WorkerError(f"命令 {command} 返回失败状态：{result}")
        token.check()
    except WorkerCancelled as exc:
        emit({"type": "task_finished", "task_id": task_id, "status": "stopped"})
        emit({"type": "log", "message": str(exc)})
        if emit_run_finished:
            emit({"type": "run_finished", "status": "stopped"})
        return "stopped"
    except Exception as exc:
        emit({"type": "task_finished", "task_id": task_id, "status": "failed"})
        emit({"type": "error", "message": str(exc) or exc.__class__.__name__})
        if emit_run_finished:
            emit({"type": "run_finished", "status": "failed"})
        return "failed"
    skipped = bool(getattr(args, "task_skipped_reason", None))
    emit({"type": "task_finished", "task_id": task_id, "status": "skipped" if skipped else "completed"})
    status = "partial" if skipped else ("dry_run_completed" if args.dry_run else "completed")
    if emit_run_finished:
        emit({"type": "run_finished", "status": status})
    return status


class _LogWriter(io.TextIOBase):
    """把现有脚本逐行输出转成桌面协议中的日志事件。"""

    def __init__(self, emit: Callable[[dict[str, object]], None]) -> None:
        self.emit = emit
        self.pending = ""

    def write(self, value: str) -> int:
        self.pending += value
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            if line:
                self.emit({"type": "log", "message": line})
        return len(value)

    def flush(self) -> None:
        if self.pending:
            self.emit({"type": "log", "message": self.pending})
            self.pending = ""


def run_request(
    request: object,
    emit: Callable[[dict[str, object]], None] | None = None,
    *,
    token: CancellationToken | None = None,
) -> str:
    """读取桌面任务请求，执行受限命令或每日任务选择并写出 JSONL 事件。"""
    emit = emit or _write_event
    token = token or CancellationToken()
    if not isinstance(request, dict):
        raise WorkerError("run 请求必须是 JSON 对象")
    mode = request.get("mode")
    dry_run = request.get("dry_run", False)
    if not isinstance(dry_run, bool):
        raise WorkerError("dry_run 必须是布尔值")
    args_values = request.get("args", [])
    # 完整日常命令也统一进入阶段执行器，保证它与日常页共享同一份阶段参数。
    if mode == "command" and request.get("command") == "daily-rewards":
        daily_command_args = parse_command_args("daily-rewards", args_values, dry_run=dry_run)
        legacy_start_tasks = {
            2: "calendar", 3: "welfare", 4: "mail", 5: "legion.daily_cut",
            6: "journey.resources", 7: "base.cafeteria", 8: "shop.resource_gold",
        }
        requested_tasks = list(DAILY_TASK_IDS)
        from_task = daily_command_args.from_task
        if from_task is None and daily_command_args.from_step != 1:
            start_task = legacy_start_tasks[daily_command_args.from_step]
            start_index = DAILY_TASK_IDS.index(start_task)
            requested_tasks = [task_id for task_id in requested_tasks if DAILY_TASK_IDS.index(task_id) >= start_index]
        # 转为桌面阶段流程时保留窗口、后端和奖励 gate 参数，只移除 CLI 的两种起点语法。
        phase_legacy_args: list[str] = []
        skip_next = False
        for value in args_values:
            if skip_next:
                skip_next = False
                continue
            if value in {"--from-step", "--from-task"}:
                skip_next = True
                continue
            if value.startswith("--from-step=") or value.startswith("--from-task="):
                continue
            phase_legacy_args.append(value)
        request = {
            **request,
            "mode": "daily",
            "command": "",
            "args": phase_legacy_args,
            "task_ids": requested_tasks,
            "from_task": from_task,
        }
        mode = "daily"
        args_values = request["args"]
    if mode == "command":
        command = request.get("command")
        if not isinstance(command, str):
            raise WorkerError("command 模式必须指定命令 ID")
        args = parse_command_args(command, args_values, dry_run=dry_run)
        previous_cancel = _install_cancellation(token)
        status = "failed"
        try:
            with contextlib.redirect_stdout(_LogWriter(emit)), contextlib.redirect_stderr(_LogWriter(emit)):
                status = _run_single_command(command, args, emit, token, emit_run_finished=False)
        finally:
            with contextlib.redirect_stdout(_LogWriter(emit)), contextlib.redirect_stderr(_LogWriter(emit)):
                _restore_cancellation(previous_cancel)
                if not dry_run:
                    common.end_input_session()
        emit({"type": "run_finished", "status": status})
        return status
    if mode != "daily":
        raise WorkerError("mode 必须是 daily 或 command")
    if request.get("command") not in (None, ""):
        raise WorkerError("daily 模式不能设置 command")
    if not isinstance(args_values, list) or any(not isinstance(value, str) for value in args_values):
        raise WorkerError("args 必须是字符串数组")
    task_ids = request.get("task_ids", list(DAILY_TASK_IDS))
    from_task = request.get("from_task")
    plan = build_daily_plan(task_ids, from_task)
    # 在开始逐任务事件前报告实际执行计划，支持完整日常命令的起点与进度总数。
    planned_task_ids = [task_id for phase in plan for task_id in phase.task_ids]
    emit({"type": "run_plan", "task_count": len(planned_task_ids), "task_ids": planned_task_ids})
    # 每个阶段的 argv 都单独校验，确保 UI 配置只作用于对应业务命令。
    phase_arguments_by_id = request.get("phase_args", {})
    if not isinstance(phase_arguments_by_id, dict) or any(
        not isinstance(phase_id, str)
        or not isinstance(values, list)
        or any(not isinstance(value, str) for value in values)
        for phase_id, values in phase_arguments_by_id.items()
    ):
        raise WorkerError("phase_args 必须是阶段 ID 到字符串数组的映射")
    known_phase_ids = set(DAILY_PHASE_ORDER)
    if any(phase_id not in known_phase_ids for phase_id in phase_arguments_by_id):
        raise WorkerError("phase_args 包含未知阶段")
    daily_args = parse_command_args("daily-rewards", args_values, dry_run=dry_run)
    explicit_daily_arguments = _explicit_argument_destinations("daily-rewards", args_values)
    if daily_args.from_step != 1:
        raise WorkerError("桌面每日任务使用 task_ids 和 from_task 选择任务，不接受 from-step")
    if daily_args.from_task is not None:
        raise WorkerError("桌面每日任务使用 from_task 字段选择起点，不接受 --from-task")
    previous_cancel = _install_cancellation(token)
    try:
        with contextlib.redirect_stdout(_LogWriter(emit)), contextlib.redirect_stderr(_LogWriter(emit)):
            token.check()
            if dry_run:
                bounds = daily_args.mock_bounds
            else:
                bounds = _preflight_live(fit=bool(daily_args.fit), token=token)
            first_task = plan[0].task_ids[0]

            def phase_runner(phase: DailyPhase, report_task: Callable[[str, str], None]) -> None:
                token.check()
                is_first_phase = phase is plan[0]
                explicit = from_task if is_first_phase else None
                has_previous = not is_first_phase
                _call_phase_with_events(
                    phase,
                    report_task,
                    bounds=bounds,
                    backend=daily_args.backend,
                    dry_run=dry_run,
                    explicit_from_task=explicit,
                    has_previous_task=has_previous,
                    phase_arguments=phase_arguments_by_id.get(phase.id, ()),
                    explicit_phase_arguments=_explicit_argument_destinations(
                        DAILY_PHASE_COMMANDS[phase.id], phase_arguments_by_id.get(phase.id, ())
                    ),
                    pass_gate_values=(
                        daily_args.pass_free_claim_state if "pass_free_claim_state" in explicit_daily_arguments else None,
                        daily_args.pass_work_plan_sign_state if "pass_work_plan_sign_state" in explicit_daily_arguments else None,
                    ),
                    armed_gate_values=(
                        daily_args.armed_skip_animation_state if "armed_skip_animation_state" in explicit_daily_arguments else None,
                        daily_args.armed_free_draw_state if "armed_free_draw_state" in explicit_daily_arguments else None,
                        daily_args.armed_task_claims if "armed_task_claims" in explicit_daily_arguments else None,
                    ),
                    mechanical_shock_gate_values=(
                        daily_args.mechanical_shock_skip_animation_state if "mechanical_shock_skip_animation_state" in explicit_daily_arguments else None,
                        daily_args.mechanical_shock_task_claims if "mechanical_shock_task_claims" in explicit_daily_arguments else None,
                        daily_args.mechanical_shock_mech_fight_claim_state if "mechanical_shock_mech_fight_claim_state" in explicit_daily_arguments else None,
                    ),
                    mimic_gate_values=(
                        daily_args.mimic_skip_animation_state if "mimic_skip_animation_state" in explicit_daily_arguments else None,
                        daily_args.mimic_free_draw_state if "mimic_free_draw_state" in explicit_daily_arguments else None,
                        daily_args.mimic_task_claims if "mimic_task_claims" in explicit_daily_arguments else None,
                        daily_args.mimic_one_click_claim_state if "mimic_one_click_claim_state" in explicit_daily_arguments else None,
                    ),
                )
                token.check()

            status = execute_daily_plan(
                plan, phase_runner, emit, dry_run=dry_run, emit_run_finished=False
            )
    except WorkerCancelled as exc:
        emit({"type": "log", "message": str(exc)})
        status = "stopped"
    finally:
        with contextlib.redirect_stdout(_LogWriter(emit)), contextlib.redirect_stderr(_LogWriter(emit)):
            _restore_cancellation(previous_cancel)
            if not dry_run:
                common.end_input_session()
    emit({"type": "run_finished", "status": status})
    return status


def _write_event(event: dict[str, object]) -> None:
    # 日志重定向期间仍写入真实协议流，避免递归把 JSONL 再当作普通日志。
    protocol_stream = sys.__stdout__
    protocol_stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    protocol_stream.flush()


def _read_control_messages(
    token: CancellationToken, *, stop_on_disconnect: bool = False
) -> None:
    """后台读取停止控制行，并可将桌面父进程断开转换为协作式停止。"""
    for line in sys.stdin:
        try:
            message = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(message, dict) and message.get("type") == "stop":
            token.request_stop()
    if stop_on_disconnect:
        token.request_stop()


def _install_signal_stop(token: CancellationToken) -> dict[int, object]:
    """将 SIGTERM 转为协作式停止，给当前 CGEvent 点击留出完成时间。"""
    old_handlers: dict[int, object] = {}
    for signum in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
        if signum is None:
            continue
        try:
            old_handlers[signum] = signal.signal(signum, lambda _signum, _frame: token.request_stop())
        except (ValueError, OSError):
            pass
    return old_handlers


def _restore_signal_handlers(old_handlers: dict[int, object]) -> None:
    for signum, handler in old_handlers.items():
        try:
            signal.signal(signum, handler)
        except (ValueError, OSError):
            pass


def main(argv: Sequence[str] | None = None) -> int:
    """桌面 sidecar CLI：catalog 返回目录，run 按 JSONL 请求启动一项任务。"""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("catalog", help="输出桌面任务目录 JSON")
    subparsers.add_parser("run", help="从标准输入读取一个 JSON 请求并输出 JSONL 事件")
    args = parser.parse_args(argv)
    if args.action == "catalog":
        sys.stdout.write(json.dumps(build_catalog(), ensure_ascii=False, indent=2) + "\n")
        return 0

    request_line = sys.stdin.readline()
    token = CancellationToken()
    if not request_line:
        _write_event({"type": "error", "message": "缺少 run 请求 JSON 行"})
        _write_event({"type": "run_finished", "status": "failed"})
        return 2
    try:
        request = json.loads(request_line)
    except json.JSONDecodeError as exc:
        _write_event({"type": "error", "message": f"run 请求 JSON 无效：{exc.msg}"})
        _write_event({"type": "run_finished", "status": "failed"})
        return 2
    old_handlers = _install_signal_stop(token)
    stop_on_disconnect = (
        isinstance(request, dict)
        and request.get("mode") in {"daily", "command"}
        and request.get("dry_run", False) is False
    )
    control_reader = threading.Thread(
        target=_read_control_messages,
        kwargs={"token": token, "stop_on_disconnect": stop_on_disconnect},
        daemon=True,
    )
    control_reader.start()
    try:
        status = run_request(request, token=token)
    except Exception as exc:
        _write_event({"type": "error", "message": str(exc) or exc.__class__.__name__})
        _write_event({"type": "run_finished", "status": "failed"})
        status = "failed"
    finally:
        _restore_signal_handlers(old_handlers)
    return 0 if status in {"completed", "dry_run_completed", "stopped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
