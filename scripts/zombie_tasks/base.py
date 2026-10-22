"""Base tab training-hall workflow."""

from __future__ import annotations

from ..zombie_common import *
from ..zombie_actions import *
from .resume import (
    LOCAL_TASK_IDS,
    print_task_selection,
    report_desktop_task,
    select_enabled_task_suffix,
    select_task_suffix,
)

BUSINESS_WAITS = {
    "abyss_challenge": 3.0,
    "abyss_entry": 0.5,
    "abyss_fail_return": 2.0,
    "battle_challenge": 1.0,
    "core_trial": 0.5,
    "global_expedition_challenge": 1.0,
    "global_rescue_challenge": 1.5,
    "training_hall": 2.5,
    "terminal_crisis_confirm": 0.5,
}


def _click_action(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    action: str,
    bounds: Bounds,
    *,
    dismiss: bool = False,
    reward: bool = False,
    post_wait_seconds: float | None = None,
) -> str:
    if dismiss:
        backend = perform_dismiss_click(*points[action], args.backend, bounds)
    elif reward:
        backend = perform_reward_click(*points[action], args.backend, bounds)
    elif action in BOTTOM_TAB_ACTION_NAMES:
        backend = perform_tab_click(*points[action], args.backend, bounds)
    elif post_wait_seconds is not None:
        backend = perform_click(*points[action], args.backend, bounds, wait_after=False)
        sleep_between(post_wait_seconds + 0.5)
    else:
        backend = perform_action(action, *points[action], args.backend, bounds, BUSINESS_WAITS)
    verb = "dismissed" if dismiss else "clicked"
    print(f"base training hall: {action} ({verb}) via {backend}", flush=True)
    return backend


def scroll_to_bottom(
    args: argparse.Namespace,
    start_action: str = "training_hall_drag_start",
    end_action: str = "training_hall_drag_end",
) -> None:
    """Scroll a focused base-task list down with CoreGraphics."""
    if getattr(args, "skip_scroll", False):
        return
    bounds = args.active_bounds
    x1, y1 = scale_point(ACTIONS[start_action], bounds)
    x2, y2 = scale_point(ACTIONS[end_action], bounds)
    perform_drag(x1, y1, x2, y2, bounds)
    sleep_between(1.5)


def _run_deep_abyss_subtask(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    bounds: Bounds,
) -> None:
    """深渊挑战：进入挑战后暂停退出，再尝试两次扫荡并返回训练大厅。"""
    _click_action(args, points, "abyss_entry", bounds)
    _click_action(args, points, "abyss_challenge", bounds)
    _click_action(args, points, "reward_dismiss", bounds, post_wait_seconds=0.5)
    _click_action(args, points, "abyss_pause", bounds)
    _click_action(args, points, "abyss_pause_exit", bounds)
    _click_action(args, points, "abyss_fail_return", bounds)

    for index in range(2):
        _click_action(args, points, "abyss_sweep", bounds, reward=True)
        _click_action(args, points, "reward_dismiss", bounds, dismiss=True)
        print(f"base training hall: Deep Abyss sweep {index + 1}/2 attempted", flush=True)

    _click_action(args, points, "abyss_back", bounds)

def command_base_training_hall_deep_abyss(args: argparse.Namespace) -> int:
    """从已打开的训练大厅列表单独执行深渊挑战子任务。"""
    bounds = prepare_command_bounds(args)
    args.active_bounds = bounds
    names = (
        "abyss_entry", "abyss_challenge",
        "abyss_monster_info_confirm", "abyss_skill_select_confirm", "abyss_pause",
        "abyss_pause_exit", "abyss_fail_return", "abyss_sweep", "reward_dismiss",
        "abyss_back", "base_tab",
    )
    points = scaled_points(bounds, *names)
    if args.dry_run:
        print(f"Deep Abyss subtask dry-run: points={points}")
        return 0

    _run_deep_abyss_subtask(args, points, bounds)
    print("Deep Abyss subtask complete: challenge failed, two sweeps attempted, returned to training hall", flush=True)
    return 0


def _purchase_play_shop_item(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    item_action: str,
    bounds: Bounds,
) -> None:
    backend = perform_click(*points[item_action], args.backend, bounds)
    print(f"base training hall shop: opened {item_action} via {backend}", flush=True)
    perform_click(*points["play_shop_max"], args.backend, bounds)
    perform_reward_click(*points["play_shop_buy"], args.backend, bounds)
    perform_dismiss_click(*points["play_shop_reward_dismiss"], args.backend, bounds)
    perform_click(*points["play_shop_modal_close"], args.backend, bounds)
    print(f"base training hall shop: completed {item_action}", flush=True)


def command_base_training_hall_shop(args: argparse.Namespace) -> int:
    """玩法商店：依次购买强化剂、枪械图纸、基建耗材和随机技能手册后关闭商店。"""
    from_task = getattr(args, "from_task", None)
    selection = select_task_suffix(
        LOCAL_TASK_IDS["base-training-hall-shop"],
        from_task,
        "base-training-hall-shop",
    )
    print_task_selection("base-training-hall-shop", selection, dry_run=args.dry_run)
    bounds = prepare_command_bounds(args)
    args.active_bounds = bounds
    names = (
        "play_shop", "play_shop_enhancer", "play_shop_battle_tab",
        "play_shop_battle_drag_start", "play_shop_battle_drag_end", "play_shop_gun_blueprint",
        "play_shop_tabs_drag_start", "play_shop_tabs_drag_end", "play_shop_element_tab",
        "play_shop_base_material", "play_shop_legion_tab", "play_shop_skill_manual",
        "play_shop_max", "play_shop_buy", "play_shop_reward_dismiss", "play_shop_modal_close",
        "play_shop_close",
    )
    points = scaled_points(bounds, *names)
    if args.dry_run:
        print(f"base training hall shop dry-run: tasks={selection.remaining}, skipped={selection.skipped}, points={points}")
        return 0

    if from_task is None:
        perform_click(*points["play_shop"], args.backend, bounds)
    tasks = set(selection.remaining)
    if "base_powder" in tasks:
        _purchase_play_shop_item(args, points, "play_shop_enhancer", bounds)
        if "gun_blueprint" in tasks:
            perform_click(*points["play_shop_battle_tab"], args.backend, bounds)
            scroll_to_bottom(args, "play_shop_battle_drag_start", "play_shop_battle_drag_end")
    if "gun_blueprint" in tasks:
        _purchase_play_shop_item(args, points, "play_shop_gun_blueprint", bounds)
        if "base_materials" in tasks:
            scroll_to_bottom(args, "play_shop_tabs_drag_start", "play_shop_tabs_drag_end")
            perform_click(*points["play_shop_element_tab"], args.backend, bounds)
    if "base_materials" in tasks:
        _purchase_play_shop_item(args, points, "play_shop_base_material", bounds)
        # 随机技能手册紧接基建耗材购买，并复用同一最大数量购买流程。
        perform_click(*points["play_shop_legion_tab"], args.backend, bounds)
        _purchase_play_shop_item(args, points, "play_shop_skill_manual", bounds)
    sleep_between(0.5)
    perform_click(*points["play_shop_close"], args.backend, bounds)
    print(f"base training hall shop complete: attempted {selection.remaining} and closed shop", flush=True)
    return 0


def _run_global_rescue_subtask(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    bounds: Bounds,
) -> None:
    """寰球救援：进入挑战，领取免费奖励后返回训练大厅。"""
    _click_action(args, points, "global_rescue_challenge", bounds)
    _click_action(args, points, "global_rescue_free", bounds, reward=True)
    _click_action(args, points, "training_reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "training_hall_back", bounds)


def _run_global_expedition_subtask(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    bounds: Bounds,
) -> None:
    """寰球远征：进入远征页领取免费奖励，关闭弹窗并返回训练大厅。"""
    _click_action(args, points, "global_expedition_challenge", bounds)
    _click_action(args, points, "global_expedition_free", bounds, reward=True)
    _click_action(args, points, "reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "global_expedition_back", bounds)


def _run_terminal_crisis_subtask(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    bounds: Bounds,
) -> None:
    """终末危机：滚动列表进入挑战，扫荡并确认奖励后返回训练大厅。"""
    scroll_to_bottom(args)
    if not getattr(args, "skip_scroll", False):
        print("base training hall: scroll_to_bottom (scrolled) via cgclick", flush=True)
    _click_action(args, points, "terminal_crisis_challenge", bounds)
    _click_action(args, points, "terminal_crisis_sweep", bounds)
    _click_action(args, points, "terminal_crisis_confirm", bounds, reward=True)
    _click_action(args, points, "training_reward_dismiss", bounds, dismiss=True)
    sleep_between(0.5)
    _click_action(args, points, "training_hall_back", bounds)


def _run_battlefield_contest_subtask(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    bounds: Bounds,
) -> None:
    """战场争霸：领取城堡奖励，按指定次数扫荡列表末项后返回训练大厅。"""
    _click_action(args, points, "battle_challenge", bounds)
    _click_action(args, points, "battle_castle", bounds)
    _click_action(args, points, "reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "battle_modal_challenge", bounds)
    scroll_to_bottom(args, "battle_modal_drag_start", "battle_modal_drag_end")
    if not getattr(args, "skip_scroll", False):
        print("base training hall: battle_modal_scroll_to_bottom (scrolled) via cgclick", flush=True)
    for index in range(args.battle_times):
        _click_action(args, points, "battle_sweep_last", bounds, reward=True)
        _click_action(args, points, "battle_reward_dismiss", bounds, dismiss=True)
        print(f"base training hall: battlefield sweep {index + 1}/{args.battle_times} complete", flush=True)
    _click_action(args, points, "battle_modal_close", bounds)
    _click_action(args, points, "training_hall_back", bounds)


def _run_element_trial_subtask(
    args: argparse.Namespace,
    points: dict[str, tuple[int, int]],
    bounds: Bounds,
) -> None:
    """元素试炼：进入核心试炼领取挂机收益，执行十次扫荡后返回训练大厅。"""
    _click_action(args, points, "element_challenge", bounds)
    _click_action(args, points, "core_trial", bounds)
    _click_action(args, points, "idle_button", bounds)
    _click_action(args, points, "idle_claim", bounds, reward=True)
    _click_action(args, points, "reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "idle_cancel", bounds)
    _click_action(args, points, "core_sweep", bounds)
    _click_action(args, points, "core_sweep_ten", bounds, reward=True)
    _click_action(args, points, "reward_dismiss", bounds, dismiss=True)
    _click_action(args, points, "core_sweep_close", bounds)
    _click_action(args, points, "core_trial_back", bounds)
    _click_action(args, points, "element_back", bounds)


def _command_training_hall_subtask(
    args: argparse.Namespace,
    label: str,
    action_names: tuple[str, ...],
    route: Callable[[argparse.Namespace, dict[str, tuple[int, int]], Bounds], None],
    *,
    scroll_hall_to_bottom: bool = False,
) -> int:
    bounds = prepare_command_bounds(args)
    args.active_bounds = bounds
    points = scaled_points(bounds, *action_names)
    if args.dry_run:
        print(f"{label} subtask dry-run: points={points}")
        return 0
    if scroll_hall_to_bottom:
        scroll_to_bottom(args)
        print("base training hall: scroll_to_bottom (scrolled) via cgclick", flush=True)
    route(args, points, bounds)
    print(f"{label} subtask complete: returned to training hall", flush=True)
    return 0


def command_base_training_hall_global_rescue(args: argparse.Namespace) -> int:
    """从已打开的训练大厅列表单独执行寰球救援子任务。"""
    return _command_training_hall_subtask(
        args,
        "Global Rescue",
        ("global_rescue_challenge", "global_rescue_free", "training_reward_dismiss", "training_hall_back"),
        _run_global_rescue_subtask,
    )


def command_base_training_hall_global_expedition(args: argparse.Namespace) -> int:
    """从已打开的训练大厅列表单独执行寰球远征免费奖励子任务。"""
    return _command_training_hall_subtask(
        args,
        "Global Expedition",
        (
            "global_expedition_challenge", "global_expedition_free", "reward_dismiss",
            "global_expedition_back", "base_tab", "training_hall",
        ),
        _run_global_expedition_subtask,
    )


def command_base_training_hall_terminal_crisis(args: argparse.Namespace) -> int:
    """从已打开的训练大厅列表单独执行终末危机子任务。"""
    return _command_training_hall_subtask(
        args,
        "Terminal Crisis",
        ("terminal_crisis_challenge", "terminal_crisis_sweep", "terminal_crisis_confirm", "training_reward_dismiss", "training_hall_back"),
        _run_terminal_crisis_subtask,
    )


def command_base_training_hall_battlefield_contest(args: argparse.Namespace) -> int:
    """从已打开的训练大厅列表单独执行战场争霸，扫荡次数由 battle_times 指定。"""
    if args.battle_times < 1:
        raise ClickError("--battle-times must be >= 1")
    return _command_training_hall_subtask(
        args,
        "Battlefield Contest",
        ("battle_challenge", "battle_castle", "reward_dismiss", "battle_modal_challenge", "battle_sweep_last", "battle_reward_dismiss", "battle_modal_close", "training_hall_back"),
        _run_battlefield_contest_subtask,
        scroll_hall_to_bottom=True,
    )


def command_base_training_hall_element_trial(args: argparse.Namespace) -> int:
    """从已打开的训练大厅列表单独执行元素试炼子任务。"""
    return _command_training_hall_subtask(
        args,
        "Element Trial",
        ("element_challenge", "core_trial", "idle_button", "idle_claim", "reward_dismiss", "idle_cancel", "core_sweep", "core_sweep_ten", "core_sweep_close", "core_trial_back", "element_back"),
        _run_element_trial_subtask,
        scroll_hall_to_bottom=True,
    )


def command_base_training_hall(args: argparse.Namespace) -> int:
    """基地每日组合任务：按顺序处理食堂、训练挑战和玩法商店，并为桌面任务补齐导航。"""
    from_task = getattr(args, "from_task", None)
    selection = select_enabled_task_suffix(
        LOCAL_TASK_IDS["base-training-hall"],
        from_task,
        "base-training-hall",
        getattr(args, "desktop_task_ids", None),
    )
    print_task_selection("base-training-hall", selection, dry_run=args.dry_run)
    if args.battle_times < 1:
        raise ClickError("--battle-times must be >= 1")
    bounds = prepare_command_bounds(args)
    args.active_bounds = bounds
    names = (
        "base_tab", "cafeteria", "cafeteria_claim", "cafeteria_back", "training_reward_dismiss", "battle_reward_dismiss",
        "training_hall", "global_rescue_challenge", "global_rescue_free",
        "global_expedition_challenge", "global_expedition_free", "global_expedition_back", "abyss_entry",
        "abyss_challenge", "abyss_monster_info_confirm",
        "abyss_skill_select_confirm", "abyss_pause", "abyss_pause_exit", "abyss_fail_return",
        "abyss_sweep", "abyss_back", "terminal_crisis_challenge",
        "terminal_crisis_sweep", "terminal_crisis_confirm", "battle_challenge", "battle_castle", "battle_modal_challenge",
        "battle_modal_drag_start", "battle_modal_drag_end", "battle_sweep_last", "reward_dismiss", "battle_modal_close",
        "training_hall_back", "element_challenge", "core_trial", "idle_button",
        "idle_claim", "idle_cancel", "core_sweep", "core_sweep_ten", "core_sweep_close", "core_trial_back",
        "element_back",
    )
    points = scaled_points(bounds, *names)
    if args.dry_run:
        print(
            f"base training hall dry-run: tasks={selection.remaining}, skipped={selection.skipped}, "
            f"battle_times={args.battle_times}, skip_scroll={args.skip_scroll}, points={points}"
        )
        for task_id in selection.remaining:
            report_desktop_task(args, task_id, "started")
            report_desktop_task(args, task_id, "completed")
        return 0

    tasks = set(selection.remaining)
    hall_at_bottom = False

    # 桌面删减前置阶段时，仅导航到当前首项所需页面，不额外领取奖励。
    navigate_pending = bool(getattr(args, "desktop_navigate_base", False))

    def start_base_task(task_id: str) -> None:
        nonlocal navigate_pending
        report_desktop_task(args, task_id, "started")
        if navigate_pending:
            _click_action(args, points, "base_tab", bounds)
            if getattr(args, "desktop_navigate_training_hall", False):
                _click_action(args, points, "training_hall", bounds)
            navigate_pending = False

    if "cafeteria" in tasks:
        start_base_task("cafeteria")
        if from_task is None and not getattr(args, "desktop_navigate_base", False):
            _click_action(args, points, "base_tab", bounds)
        # 食堂：领取免费奖励后返回基地。
        _click_action(args, points, "cafeteria", bounds)
        _click_action(args, points, "cafeteria_claim", bounds, reward=True)
        _click_action(args, points, "training_reward_dismiss", bounds, dismiss=True)
        _click_action(args, points, "cafeteria_back", bounds)
        _click_action(args, points, "training_hall", bounds)
        report_desktop_task(args, "cafeteria", "completed")

    if "global_rescue" in tasks:
        start_base_task("global_rescue")
        _run_global_rescue_subtask(args, points, bounds)
        report_desktop_task(args, "global_rescue", "completed")
    if "global_expedition" in tasks:
        start_base_task("global_expedition")
        _run_global_expedition_subtask(args, points, bounds)
        report_desktop_task(args, "global_expedition", "completed")
    if "deep_abyss" in tasks:
        start_base_task("deep_abyss")
        _run_deep_abyss_subtask(args, points, bounds)
        # Abyss returns to the main game; restore the hall page for later tasks.
        _click_action(args, points, "base_tab", bounds)
        _click_action(args, points, "training_hall", bounds)
        hall_at_bottom = False
        report_desktop_task(args, "deep_abyss", "completed")
    if "terminal_crisis" in tasks:
        start_base_task("terminal_crisis")
        _run_terminal_crisis_subtask(args, points, bounds)
        # 终末危机会先滚到底；后续底部卡片可沿用这个大厅位置。
        hall_at_bottom = True
        report_desktop_task(args, "terminal_crisis", "completed")
    if "battlefield_contest" in tasks:
        start_base_task("battlefield_contest")
        # 若终末危机被移除，仍须先把大厅列表滚到底才能进入巅峰争霸。
        if not hall_at_bottom:
            scroll_to_bottom(args)
            if not getattr(args, "skip_scroll", False):
                print("base training hall: scroll_to_bottom before Battlefield Contest via cgclick", flush=True)
        _run_battlefield_contest_subtask(args, points, bounds)
        hall_at_bottom = True
        report_desktop_task(args, "battlefield_contest", "completed")
    if "element_trial" in tasks:
        start_base_task("element_trial")
        # 元素试炼同样位于训练大厅底部，必要时补做列表导航。
        if not hall_at_bottom:
            scroll_to_bottom(args)
            if not getattr(args, "skip_scroll", False):
                print("base training hall: scroll_to_bottom before Element Trial via cgclick", flush=True)
        _run_element_trial_subtask(args, points, bounds)
        hall_at_bottom = True
        report_desktop_task(args, "element_trial", "completed")
    if "play_shop" in tasks:
        start_base_task("play_shop")
        shop_args = argparse.Namespace(**vars(args))
        shop_args.mock_bounds = bounds
        shop_args.fit = False
        shop_args.dry_run = False
        shop_args.from_task = None
        shop_args.skip_scroll = False
        shop_args.desktop_task_ids = None
        shop_args.desktop_task_event = None
        command_base_training_hall_shop(shop_args)
        report_desktop_task(args, "play_shop", "completed")
    sleep_between(0.5)
    backend = _click_action(args, points, "training_hall_back", bounds)
    print(
        f"base training hall complete: attempted {selection.remaining}; returned to base via {backend}"
    )
    return 0
