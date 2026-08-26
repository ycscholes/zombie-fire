#!/usr/bin/env python3
"""Fixed-coordinate click helper for the 向僵尸开炮 WeChat mini game.

Coordinates are authored against the Computer Use screenshot space that is
usually about 508x949, then scaled to the current front WeChat window.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, Tuple


BASE_WIDTH = 508
BASE_HEIGHT = 949
MIN_WIDTH = 420
MIN_HEIGHT = 760
ASPECT_MIN = 0.43
ASPECT_MAX = 0.68
# Keep a short randomized pause between helper clicks.
POST_CLICK_WAIT_MIN = 0.5
POST_CLICK_WAIT_MAX = 1.0
DISMISS_POST_WAIT_SECONDS = 1.0
MIN_WAIT_SECONDS = 0.5
CLICK_HOLD_SECONDS = 0.08
CLICK_HOLD_MILLISECONDS = 80
WINDOW_FOCUS_TIMEOUT_SECONDS = 8.0
POST_AD_READY_TIMEOUT_SECONDS = 8.0
POST_AD_READY_POLL_SECONDS = 0.4
CLICK_BACKENDS = ("auto", "cgclick", "quartz", "cliclick", "system-events")
NON_OPERATING_COMMANDS = frozenset({"list", "state", "self-test", "dry-run"})
WECHAT_NAMES = {"微信", "WeChat", "Weixin", "WeApp", "小程序"}
WECHAT_BUNDLE_HINTS = ("com.tencent.xin", "com.tencent.wechat", "com.tencent.flue")
CGCLICK_BIN: str | None = None
SKILL_ROOT = Path(__file__).resolve().parents[1]
CGCLICK_CACHE_DIR = SKILL_ROOT / ".generated"
CGCLICK_BIN_PATH = CGCLICK_CACHE_DIR / "zombie_cgclick"
CGCLICK_SOURCE_PATH = CGCLICK_CACHE_DIR / "zombie_cgclick.c"
CGCLICK_SOURCE = r"""
#include <ApplicationServices/ApplicationServices.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: zombie_cgclick x y\n"); return 2; }
  double x = atof(argv[1]);
  double y = atof(argv[2]);
  CGPoint p = CGPointMake(x, y);
  CGEventSourceRef src = CGEventSourceCreate(kCGEventSourceStateHIDSystemState);
  if (!src) return 3;
  CGEventRef move = CGEventCreateMouseEvent(src, kCGEventMouseMoved, p, kCGMouseButtonLeft);
  CGEventRef down = CGEventCreateMouseEvent(src, kCGEventLeftMouseDown, p, kCGMouseButtonLeft);
  CGEventRef up = CGEventCreateMouseEvent(src, kCGEventLeftMouseUp, p, kCGMouseButtonLeft);
  if (!move || !down || !up) return 4;
  CGEventSetIntegerValueField(down, kCGMouseEventClickState, 1);
  CGEventSetIntegerValueField(up, kCGMouseEventClickState, 1);
  CGEventPost(kCGHIDEventTap, move);
  CGEventPost(kCGHIDEventTap, down);
  usleep(80000);
  CGEventPost(kCGHIDEventTap, up);
  CFRelease(move);
  CFRelease(down);
  CFRelease(up);
  CFRelease(src);
  return 0;
}
"""


@dataclass(frozen=True)
class Action:
    x: int
    y: int
    desc: str


ACTIONS: Dict[str, Action] = {
    "patrol_truck": Action(82, 738, "home patrol truck"),
    "patrol_claim": Action(347, 696, "patrol income claim"),
    "quick_patrol": Action(143, 697, "quick patrol/ad patrol button"),
    "quick_patrol_icon": Action(120, 696, "quick patrol left icon/video area"),
    "patrol_close": Action(422, 237, "close patrol panel"),
    "reward_dismiss": Action(250, 820, "dismiss reward popup"),
    "ad_close_top": Action(468, 75, "top-right ad close"),
    "ad_close_lower": Action(468, 578, "lower floating ad/card close"),
    "calendar_top": Action(318, 119, "top calendar entry on home"),
    "calendar_gift": Action(340, 270, "calendar visible gift"),
    "calendar_close": Action(423, 202, "calendar weekly/activity page close button"),
    "right_menu": Action(428, 162, "home right-side hamburger expandable menu"),
    "mail_entry": Action(390, 211, "mail entry after opening the top-right menu"),
    "mail_claim_all": Action(252, 720, "mail one-click claim button"),
    "mail_reward_popup_dismiss": Action(250, 315, "dismiss mail reward popup or safely tap mail header"),
    "mail_close": Action(425, 226, "mail page close button"),
    "mail_menu_dismiss": Action(250, 450, "safe home-center tap to dismiss the top-right menu"),
    "welfare_cluster": Action(428, 392, "right-side welfare/gift cluster"),
    "welfare_reward_popup_dismiss": Action(250, 600, "dismiss the seven-day welfare free-reward popup"),
    "pass_entry": Action(430, 332, "right-side battle pass entry on home"),
    "pass_free_claim": Action(112, 837, "battle pass free one-click claim"),
    "work_plan_tab": Action(354, 902, "battle pass work-plan tab"),
    "work_plan_sign": Action(387, 844, "work-plan free sign-in button"),
    "battle_tab": Action(250, 900, "bottom battle tab"),
    "legion_tab": Action(367, 900, "bottom legion tab"),
    "journey_tab": Action(404, 900, "bottom journey tab"),
    "base_tab": Action(312, 900, "bottom base tab"),
    "base_back": Action(38, 79, "return from base to home"),
    "training_hall": Action(164, 425, "base training hall entry"),
    "training_hall_back": Action(84, 914, "return to training hall"),
    "battle_challenge": Action(394, 700, "battlefield contest challenge"),
    "battle_castle": Action(92, 760, "battlefield contest lower-left castle"),
    "battle_sweep_first": Action(402, 270, "first battlefield contest sweep"),
    "battle_modal_close": Action(425, 228, "close battlefield contest modal"),
    "element_challenge": Action(394, 700, "element trial challenge"),
    "core_trial": Action(252, 500, "core trial entry"),
    "idle_button": Action(394, 700, "core trial idle button"),
    "idle_claim": Action(320, 580, "claim idle reward popup"),
    "idle_cancel": Action(187, 579, "cancel idle reward popup"),
    "core_sweep": Action(394, 780, "core trial sweep"),
    "core_trial_back": Action(84, 914, "return from core trial"),
    "element_back": Action(84, 914, "return from element trial"),
    "journey_gold_claim": Action(368, 444, "visible journey gold resource bubble"),
    "journey_wood_claim": Action(229, 544, "visible journey wood resource bubble"),
    "legion_daily_cut": Action(282, 548, "legion daily-cut entry"),
    "legion_cut_once": Action(254, 797, "free daily-cut button before it becomes a diamond cost"),
    "legion_foreign_challenge": Action(121, 356, "legion foreign challenge entry"),
    "legion_sweep": Action(200, 909, "foreign challenge free sweep button"),
    "legion_sweep_cancel": Action(187, 579, "foreign challenge sweep cancellation"),
    "legion_sweep_confirm": Action(321, 579, "foreign challenge free sweep confirmation"),
    "legion_reward_left": Action(82, 116, "left reward tab inside foreign challenge"),
    "legion_reward_claim_top": Action(356, 302, "top visible legion reward claim button"),
    "legion_reward_claim_row1": Action(356, 270, "visible legion reward claim row 1"),
    "legion_reward_claim_row2": Action(356, 359, "visible legion reward claim row 2"),
    "legion_reward_claim_row3": Action(356, 448, "visible legion reward claim row 3"),
    "legion_reward_claim_row4": Action(356, 537, "visible legion reward claim row 4"),
    "legion_reward_claim_row5": Action(356, 626, "visible legion reward claim row 5"),
    "legion_reward_claim_row6": Action(356, 715, "visible legion reward claim row 6"),
    "legion_personal_reward_tab": Action(218, 793, "personal reward tab inside foreign challenge rewards"),
    "legion_personal_reward_claim_top": Action(356, 302, "first visible personal legion reward claim"),
    "legion_reward_panel_close": Action(427, 214, "close legion reward panel"),
    "legion_foreign_challenge_back": Action(86, 909, "return from foreign challenge to legion"),
    "legion_reward_popup_dismiss": Action(250, 600, "dismiss legion reward popup"),
    "legion_modal_close": Action(425, 228, "close legion inner modal"),
    "shop_tab": Action(84, 885, "bottom-left shop tab"),
    "shop_special_pack_tab": Action(405, 849, "shop special-pack tab"),
    "shop_gold_free": Action(253, 413, "shop special-pack direct free gold"),
    "back_top_left": Action(38, 79, "top-left back button"),
    "back_bottom_left": Action(84, 914, "bottom-left page back button"),
    "close_top_right": Action(468, 75, "top-right close button"),
}


@dataclass(frozen=True)
class Bounds:
    app_name: str
    bundle_id: str
    x: int
    y: int
    width: int
    height: int

    @property
    def aspect(self) -> float:
        return self.width / self.height


class ClickError(RuntimeError):
    pass


class WindowStateError(ClickError):
    pass


class ClickDeliveryError(ClickError):
    pass


class AdReturnError(WindowStateError):
    pass


class PhaseRecoveryError(WindowStateError):
    pass


@dataclass
class PhaseProgress:
    name: str
    state: str = "not_entered"


@dataclass(frozen=True)
class PhaseResult:
    name: str
    status: str
    error: str | None = None


def set_phase_state(args: argparse.Namespace, state: str) -> None:
    progress = getattr(args, "phase_progress", None)
    if progress is not None:
        progress.state = state


def front_window_snapshot() -> Dict[str, object]:
    script = r'''
tell application "System Events"
  set frontProc to first application process whose frontmost is true
  set frontName to name of frontProc
  set frontBundle to ""
  try
    set frontBundle to bundle identifier of frontProc
  end try
  tell frontProc
    if (count of windows) is 0 then error "front process has no windows"
    set frontWindow to missing value
    repeat with candidateWindow in windows
      try
        if (value of attribute "AXMain" of candidateWindow) as boolean then
          set frontWindow to candidateWindow
          exit repeat
        end if
      end try
    end repeat
    if frontWindow is missing value then set frontWindow to first window
    set frontTitle to ""
    try
      set frontTitle to name of frontWindow
    end try
    set p to position of frontWindow
    set s to size of frontWindow
  end tell
end tell
return frontName & tab & frontBundle & tab & frontTitle & tab & (item 1 of p) & tab & (item 2 of p) & tab & (item 1 of s) & tab & (item 2 of s)
'''
    parts = run_osascript(script).split("\t")
    if len(parts) != 7:
        raise ClickError(f"could not parse front-window state: {parts!r}")
    app_name, bundle_id, title, x, y, width, height = parts
    return {
        "app": app_name,
        "bundle": bundle_id,
        "title": title,
        "x": int(float(x)),
        "y": int(float(y)),
        "width": int(float(width)),
        "height": int(float(height)),
    }


def classify_snapshot(snapshot: Dict[str, object]) -> str:
    bounds = Bounds(
        str(snapshot["app"]),
        str(snapshot["bundle"]),
        int(snapshot["x"]),
        int(snapshot["y"]),
        int(snapshot["width"]),
        int(snapshot["height"]),
    )
    title = str(snapshot["title"])
    if not looks_like_wechat(bounds):
        return "wrong_app"
    if "向僵尸开炮" not in title:
        return "wechat_not_game"
    try:
        validate_bounds(bounds, allow_mock=False)
    except ClickError:
        return "bad_geometry"
    return "game_ready"


def parse_bounds(raw: str) -> Bounds:
    parts = raw.split("\t")
    if len(parts) != 6:
        raise ClickError(f"could not parse bounds: {raw!r}")
    name, bundle, x, y, width, height = parts
    return Bounds(name, bundle, int(float(x)), int(float(y)), int(float(width)), int(float(height)))


def run_osascript(script: str) -> str:
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=WINDOW_FOCUS_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ClickError("window-focus osascript timed out") from exc
    if proc.returncode != 0:
        raise ClickError(proc.stderr.strip() or proc.stdout.strip() or "osascript failed")
    return proc.stdout.strip()


def front_window_bounds() -> Bounds:
    snapshot = front_window_snapshot()
    return Bounds(
        str(snapshot["app"]),
        str(snapshot["bundle"]),
        int(snapshot["x"]),
        int(snapshot["y"]),
        int(snapshot["width"]),
        int(snapshot["height"]),
    )


def fit_game_window() -> Bounds:
    script = f'''
tell application "System Events"
  repeat with candidateProc in (application processes whose background only is false)
    try
      repeat with candidateWindow in windows of candidateProc
        if (name of candidateWindow) contains "向僵尸开炮" then
          set position of candidateWindow to {{2, 33}}
          set size of candidateWindow to {{{BASE_WIDTH}, {BASE_HEIGHT}}}
          delay 0.5
          set frontName to name of candidateProc
          set frontBundle to ""
          try
            set frontBundle to bundle identifier of candidateProc
          end try
          set p to position of candidateWindow
          set s to size of candidateWindow
          return frontName & tab & frontBundle & tab & (item 1 of p) & tab & (item 2 of p) & tab & (item 1 of s) & tab & (item 2 of s)
        end if
      end repeat
    end try
  end repeat
end tell
error "向僵尸开炮 window not found"
'''
    return parse_bounds(run_osascript(script))


def parse_mock_bounds(value: str) -> Bounds:
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("mock bounds must be x,y,width,height")
    try:
        x, y, width, height = [int(float(p)) for p in parts]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("mock bounds values must be numbers") from exc
    return Bounds("MOCK", "mock", x, y, width, height)


def non_negative_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a number") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise argparse.ArgumentTypeError("value must be a finite number >= 0")
    return parsed


def get_bounds(args: argparse.Namespace) -> Bounds:
    if args.mock_bounds:
        return args.mock_bounds
    return front_window_bounds()


def prepare_command_bounds(args: argparse.Namespace) -> Bounds:
    """Resolve, validate, and lock the window bounds used by a click command."""
    bounds = get_bounds(args)
    if args.mock_bounds:
        validate_bounds(bounds, allow_mock=True)
        return bounds
    bounds = ensure_valid_game_bounds(bounds)
    focus_game_window(bounds)
    return bounds


def looks_like_wechat(bounds: Bounds) -> bool:
    if bounds.app_name in WECHAT_NAMES:
        return True
    return any(hint in bounds.bundle_id for hint in WECHAT_BUNDLE_HINTS)


def validate_bounds(bounds: Bounds, *, allow_mock: bool = False) -> None:
    if bounds.bundle_id == "mock" and allow_mock:
        return
    if not looks_like_wechat(bounds):
        raise WindowStateError(f"front app is {bounds.app_name!r} ({bounds.bundle_id}), not WeChat/WeApp")
    if bounds.width < MIN_WIDTH or bounds.height < MIN_HEIGHT:
        raise WindowStateError(f"window too small: {bounds.width}x{bounds.height}")
    if not (ASPECT_MIN <= bounds.aspect <= ASPECT_MAX):
        raise WindowStateError(
            f"window aspect {bounds.aspect:.3f} outside expected range "
            f"{ASPECT_MIN:.2f}-{ASPECT_MAX:.2f}"
        )


def ensure_valid_game_bounds(bounds: Bounds) -> Bounds:
    try:
        validate_bounds(bounds, allow_mock=False)
        return bounds
    except ClickError as first_error:
        if bounds.bundle_id == "mock" or not looks_like_wechat(bounds):
            raise
        fitted = fit_game_window()
        try:
            validate_bounds(fitted, allow_mock=False)
        except ClickError as second_error:
            raise ClickError(f"{first_error}; auto-fit also failed: {second_error}") from second_error
        return fitted


def ensure_unchanged_game_window(expected: Bounds) -> None:
    """Fail closed if the foreground game window changed after calibration."""
    snapshot = front_window_snapshot()
    status = classify_snapshot(snapshot)
    if status != "game_ready":
        raise WindowStateError(
            "game window is not ready before click: "
            f"{status} title={snapshot.get('title')!r} "
            f"app={snapshot.get('app')!r} bundle={snapshot.get('bundle')!r}"
        )
    current = Bounds(
        str(snapshot["app"]),
        str(snapshot["bundle"]),
        int(snapshot["x"]),
        int(snapshot["y"]),
        int(snapshot["width"]),
        int(snapshot["height"]),
    )
    if current != expected:
        raise ClickError(
            "game window changed after calibration: "
            f"expected {expected.x},{expected.y} {expected.width}x{expected.height}; "
            f"got {current.x},{current.y} {current.width}x{current.height}"
        )


def ensure_game_ready_after_ad(
    expected: Bounds,
    *,
    timeout: float = POST_AD_READY_TIMEOUT_SECONDS,
    interval: float = POST_AD_READY_POLL_SECONDS,
) -> None:
    """Wait briefly for a closed ad to return to the calibrated game window."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            ensure_unchanged_game_window(expected)
            return
        except WindowStateError as exc:
            if time.monotonic() >= deadline:
                raise AdReturnError(
                    "patrol ad did not return to the calibrated game window; "
                    "stop without trying ad_close_lower"
                ) from exc
            time.sleep(interval)


def scale_point(action: Action, bounds: Bounds) -> Tuple[int, int]:
    sx = bounds.width / BASE_WIDTH
    sy = bounds.height / BASE_HEIGHT
    return bounds.x + round(action.x * sx), bounds.y + round(action.y * sy)


def scaled_points(bounds: Bounds, *names: str) -> Dict[str, Tuple[int, int]]:
    return {name: scale_point(ACTIONS[name], bounds) for name in names}


def click_quartz(x: int, y: int) -> bool:
    try:
        import Quartz  # type: ignore
    except Exception:
        return False
    source = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    move = Quartz.CGEventCreateMouseEvent(source, Quartz.kCGEventMouseMoved, (x, y), Quartz.kCGMouseButtonLeft)
    down = Quartz.CGEventCreateMouseEvent(source, Quartz.kCGEventLeftMouseDown, (x, y), Quartz.kCGMouseButtonLeft)
    up = Quartz.CGEventCreateMouseEvent(source, Quartz.kCGEventLeftMouseUp, (x, y), Quartz.kCGMouseButtonLeft)
    if not move or not down or not up:
        return False
    Quartz.CGEventSetIntegerValueField(down, Quartz.kCGMouseEventClickState, 1)
    Quartz.CGEventSetIntegerValueField(up, Quartz.kCGMouseEventClickState, 1)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, move)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    time.sleep(CLICK_HOLD_SECONDS)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)
    return True


def click_cliclick(x: int, y: int) -> bool:
    binary = shutil.which("cliclick")
    if not binary:
        return False
    subprocess.run(
        [binary, f"m:{x},{y}", f"dd:{x},{y}", f"w:{CLICK_HOLD_MILLISECONDS}", f"du:{x},{y}"],
        check=True,
    )
    return True


def ensure_cgclick() -> bool:
    global CGCLICK_BIN
    source_matches = (
        CGCLICK_SOURCE_PATH.exists()
        and CGCLICK_SOURCE_PATH.read_text(encoding="utf-8") == CGCLICK_SOURCE
    )
    if CGCLICK_BIN and source_matches and os.path.exists(CGCLICK_BIN) and os.access(CGCLICK_BIN, os.X_OK):
        return True
    if source_matches and CGCLICK_BIN_PATH.exists() and os.access(CGCLICK_BIN_PATH, os.X_OK):
        CGCLICK_BIN = str(CGCLICK_BIN_PATH)
        return True
    CGCLICK_CACHE_DIR.mkdir(mode=0o700, exist_ok=True)
    CGCLICK_SOURCE_PATH.write_text(CGCLICK_SOURCE, encoding="utf-8")
    proc = subprocess.run(
        [
            "clang",
            "-framework",
            "ApplicationServices",
            str(CGCLICK_SOURCE_PATH),
            "-o",
            str(CGCLICK_BIN_PATH),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return False
    CGCLICK_BIN = str(CGCLICK_BIN_PATH)
    return True


def click_cgclick_bin(x: int, y: int) -> bool:
    if not ensure_cgclick():
        return False
    assert CGCLICK_BIN is not None
    subprocess.run([CGCLICK_BIN, str(x), str(y)], check=True)
    return True


def click_system_events(x: int, y: int) -> bool:
    # System Events exposes only an atomic `click at` action. Route its legacy
    # selector to cgclick so every real delivery has move/down/hold/up semantics.
    return click_cgclick_bin(x, y)


def wait_after_click() -> None:
    time.sleep(random.uniform(POST_CLICK_WAIT_MIN, POST_CLICK_WAIT_MAX))


def scroll_to_bottom(args: argparse.Namespace) -> None:
    """Scroll the training-hall surface down using the verified macOS key path."""
    if getattr(args, "skip_scroll", False):
        return
    for _ in range(4):
        proc = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to key code 121'],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise ClickError(f"training hall scroll failed: {proc.stderr.strip()}")


def command_base_training_hall(args: argparse.Namespace) -> int:
    """Run the verified free Battlefield Contest and Element Trial route."""
    if args.battle_times < 1:
        raise ClickError("--battle-times must be >= 1")
    bounds = prepare_command_bounds(args)
    names = (
        "base_tab", "training_hall", "battle_challenge", "battle_castle",
        "battle_sweep_first", "reward_dismiss", "battle_modal_close",
        "training_hall_back", "element_challenge", "core_trial", "idle_button",
        "idle_claim", "idle_cancel", "core_sweep", "core_trial_back",
        "element_back", "base_back",
    )
    points = scaled_points(bounds, *names)
    if args.dry_run:
        print(f"base training hall dry-run: battle_times={args.battle_times}, skip_scroll={args.skip_scroll}, points={points}")
        return 0

    backend = perform_click(*points["base_tab"], args.backend, bounds)
    print(f"base training hall: opened base tab via {backend}", flush=True)
    backend = perform_click(*points["training_hall"], args.backend, bounds)
    print(f"base training hall: opened training hall via {backend}", flush=True)
    scroll_to_bottom(args)
    backend = perform_click(*points["battle_challenge"], args.backend, bounds)
    backend = perform_click(*points["battle_castle"], args.backend, bounds)
    backend = perform_click(*points["battle_challenge"], args.backend, bounds)
    for index in range(args.battle_times):
        backend = perform_click(*points["battle_sweep_first"], args.backend, bounds)
        backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
        print(f"battlefield contest sweep {index + 1}/{args.battle_times} via {backend}", flush=True)
    backend = perform_click(*points["battle_modal_close"], args.backend, bounds)
    backend = perform_click(*points["training_hall_back"], args.backend, bounds)
    backend = perform_click(*points["element_challenge"], args.backend, bounds)
    backend = perform_click(*points["core_trial"], args.backend, bounds)
    backend = perform_click(*points["idle_button"], args.backend, bounds)
    backend = perform_click(*points["idle_claim"], args.backend, bounds)
    backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
    backend = perform_click(*points["idle_cancel"], args.backend, bounds)
    backend = perform_click(*points["core_sweep"], args.backend, bounds)
    backend = perform_click(*points["core_trial_back"], args.backend, bounds)
    backend = perform_click(*points["element_back"], args.backend, bounds)
    backend = perform_click(*points["training_hall_back"], args.backend, bounds)
    backend = perform_click(*points["base_back"], args.backend, bounds)
    print(f"base training hall complete: attempted battle={args.battle_times} and element trial via {backend}")
    return 0


def try_click_backend(name: str, x: int, y: int) -> tuple[bool, str]:
    try:
        if name == "cgclick":
            clicked = click_cgclick_bin(x, y)
        elif name == "quartz":
            clicked = click_quartz(x, y)
        elif name == "cliclick":
            clicked = click_cliclick(x, y)
        elif name == "system-events":
            clicked = click_system_events(x, y)
        else:
            raise ClickError(f"unknown click backend {name!r}")
    except Exception as exc:
        return False, str(exc) or exc.__class__.__name__
    return (True, "") if clicked else (False, "unavailable")


def click_backend_candidates(backend: str) -> tuple[str, ...]:
    """Return the single backend selected for a click invocation."""
    if backend == "auto":
        return ("cgclick",)
    return (backend,)


def perform_click(
    x: int,
    y: int,
    backend: str = "auto",
    expected_bounds: Bounds | None = None,
    wait_after: bool = True,
) -> str:
    if expected_bounds is None:
        raise ClickDeliveryError("real clicks require calibrated game-window bounds")
    failures = []
    for _attempt in range(2):
        # 每次投递前重新聚焦游戏；弹窗或广告可能在两次操作之间抢走焦点。
        focus_game_window(expected_bounds)
        # 聚焦后仍须确认校准窗口未移动或缩放，避免固定坐标误点。
        ensure_unchanged_game_window(expected_bounds)
        for candidate in click_backend_candidates(backend):
            clicked, reason = try_click_backend(candidate, x, y)
            if clicked:
                if wait_after:
                    wait_after_click()
                return candidate
            failures.append(f"{candidate}: {reason}")
    raise ClickDeliveryError("click backend failed: " + "; ".join(failures))


def perform_dismiss_click(
    x: int,
    y: int,
    backend: str,
    expected_bounds: Bounds,
) -> str:
    """Dismiss a reward popup and wait exactly one second before continuing."""
    selected_backend = perform_click(x, y, backend, expected_bounds, False)
    time.sleep(DISMISS_POST_WAIT_SECONDS)
    return selected_backend


def sleep_between(seconds: float) -> None:
    time.sleep(max(MIN_WAIT_SECONDS, seconds - 1.0))


def run_repeated_click_flow(
    *,
    points: Dict[str, Tuple[int, int]],
    bounds: Bounds,
    backend_name: str,
    count: int,
    between: float,
    steps: tuple[tuple[str, str, float], ...],
) -> str:
    """Run a repeated action flow and return the backend used by its last click."""
    backend = ""
    for index in range(count):
        for action_name, message, wait in steps:
            click = perform_dismiss_click if "dismiss" in action_name else perform_click
            backend = click(*points[action_name], backend_name, bounds)
            print(
                message.format(index=index + 1, count=count, backend=backend),
                flush=True,
            )
            if wait > 0:
                sleep_between(wait)
        if index + 1 < count:
            sleep_between(between)
    return backend


def focus_game_window(bounds: Bounds) -> None:
    """Focus the game immediately before a click and preserve calibration."""
    focused = focus_game_window_at_start(expected_bounds=bounds)
    if focused != bounds:
        raise WindowStateError(
            "focused game window changed after calibration: "
            f"expected {bounds.x},{bounds.y} {bounds.width}x{bounds.height}; "
            f"got {focused.x},{focused.y} {focused.width}x{focused.height}"
        )


def focus_game_window_at_start(expected_bounds: Bounds | None = None) -> Bounds:
    """Raise and verify the game window before any action command runs."""
    expected_match = ""
    expected_match_end = ""
    if expected_bounds is not None:
        expected_match = (
            f"if ((item 1 of p) as integer) = {expected_bounds.x} and "
            f"((item 2 of p) as integer) = {expected_bounds.y} and "
            f"((item 1 of s) as integer) = {expected_bounds.width} and "
            f"((item 2 of s) as integer) = {expected_bounds.height} then"
        )
        expected_match_end = "end if"
    script = f'''
tell application "System Events"
  repeat with candidateProc in (application processes whose background only is false)
    try
      repeat with candidateWindow in windows of candidateProc
        if (name of candidateWindow) contains "向僵尸开炮" then
          set p to position of candidateWindow
          set s to size of candidateWindow
          {expected_match}
          set frontmost of candidateProc to true
          try
            perform action "AXRaise" of candidateWindow
          on error raiseError number raiseNumber
            try
              set value of attribute "AXMain" of candidateWindow to true
            on error mainError number mainNumber
              error "could not focus 向僵尸开炮 window: AXRaise: " & raiseError & "; AXMain: " & mainError number mainNumber
            end try
          end try
          delay 0.5
          set p to position of candidateWindow
          set s to size of candidateWindow
          set candidateName to name of candidateProc
          set candidateBundle to ""
          try
            set candidateBundle to bundle identifier of candidateProc
          end try
          return candidateName & tab & candidateBundle & tab & (item 1 of p) & tab & (item 2 of p) & tab & (item 1 of s) & tab & (item 2 of s)
          {expected_match_end}
        end if
      end repeat
    on error errMsg number errNum
      if errMsg starts with "could not focus 向僵尸开炮 window:" then error errMsg number errNum
    end try
  end repeat
end tell
error "向僵尸开炮 window not found"
'''
    target = parse_bounds(run_osascript(script))
    snapshot = front_window_snapshot()
    focused = Bounds(
        str(snapshot["app"]),
        str(snapshot["bundle"]),
        int(snapshot["x"]),
        int(snapshot["y"]),
        int(snapshot["width"]),
        int(snapshot["height"]),
    )
    title = str(snapshot["title"])
    if not looks_like_wechat(focused) or "向僵尸开炮" not in title:
        raise WindowStateError(
            "game window did not become frontmost: "
            f"title={title!r} "
            f"app={snapshot.get('app')!r} bundle={snapshot.get('bundle')!r}"
        )
    if focused != target:
        raise ClickError(
            "focused game window does not match selected target: "
            f"expected {target.x},{target.y} {target.width}x{target.height}; "
            f"got {focused.x},{focused.y} {focused.width}x{focused.height}"
        )
    return target


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


def command_patrol_ads_batch(args: argparse.Namespace) -> int:
    if args.times < 1:
        raise ClickError("--times must be >= 1")
    bounds = prepare_command_bounds(args)
    points = scaled_points(bounds, "quick_patrol", "ad_close_top", "reward_dismiss")
    if args.dry_run:
        print(
            "patrol ad batch dry-run: "
            f"times={args.times}, ad_wait={args.ad_wait}, reward_wait={args.reward_wait}, "
            f"between={args.between}, points={points}"
        )
        return 0
    backend = run_repeated_click_flow(
        points=points,
        bounds=bounds,
        backend_name=args.backend,
        count=args.times,
        between=args.between,
        steps=(
            ("quick_patrol", "patrol ad {index}/{count}: clicked watch-ad via {backend}", args.ad_wait),
            ("ad_close_top", "patrol ad {index}/{count}: clicked ad-close via {backend}", args.reward_wait),
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
    points = patrol_full_points(bounds)
    if args.dry_run:
        plan = {
            "command": "patrol-full-from-home",
            "quick_times": args.quick_times,
            "ad_times": args.ad_times,
            "fit": args.fit and not bool(args.mock_bounds),
            "waits": {
                "panel_wait": args.panel_wait,
                "claim_wait": args.claim_wait,
                "dismiss_wait": args.dismiss_wait,
                "quick_reward_wait": args.quick_reward_wait,
                "quick_between": args.quick_between,
                "ad_wait": args.ad_wait,
                "ad_close_wait": args.ad_close_wait,
                "ad_reward_wait": args.ad_reward_wait,
                "ad_between": args.ad_between,
                "close_wait": args.close_wait,
            },
            "points": points,
        }
        if args.json:
            print_json(plan, True)
        else:
            print(
                "patrol full from-home dry-run: "
                f"quick_times={args.quick_times}, ad_times={args.ad_times}, "
                f"fit={plan['fit']}, waits={plan['waits']}, points={points}"
            )
        return 0

    backend = perform_click(*points["patrol_truck"], args.backend, bounds)
    set_phase_state(args, "patrol_opened")
    print(f"patrol full: clicked patrol truck via {backend}", flush=True)
    sleep_between(args.panel_wait)

    backend = perform_click(*points["patrol_claim"], args.backend, bounds)
    print(f"patrol full: clicked patrol claim via {backend}", flush=True)
    sleep_between(args.claim_wait)
    backend = dismiss_reward_once(points, args.backend, bounds, label="patrol full claim")
    sleep_between(args.quick_between)

    for idx in range(args.quick_times):
        backend = perform_click(*points["quick_patrol"], args.backend, bounds)
        print(f"patrol full quick {idx + 1}/{args.quick_times}: clicked quick-patrol via {backend}", flush=True)
        sleep_between(args.quick_reward_wait)
        backend = dismiss_reward_once(
            points,
            args.backend,
            bounds,
            label=f"patrol full quick {idx + 1}/{args.quick_times}",
        )
        if idx + 1 < args.quick_times:
            sleep_between(args.quick_between)

    sleep_between(args.ad_between)
    for idx in range(args.ad_times):
        backend = perform_click(*points["quick_patrol"], args.backend, bounds)
        print(f"patrol full ad {idx + 1}/{args.ad_times}: clicked watch-ad via {backend}", flush=True)
        sleep_between(args.ad_wait)
        backend = perform_click(*points["ad_close_top"], args.backend, bounds)
        print(f"patrol full ad {idx + 1}/{args.ad_times}: clicked ad-close-top via {backend}", flush=True)
        sleep_between(args.ad_close_wait)
        sleep_between(args.ad_reward_wait)
        ensure_game_ready_after_ad(bounds)
        backend = dismiss_reward_once(
            points,
            args.backend,
            bounds,
            label=f"patrol full ad {idx + 1}/{args.ad_times}",
        )
        if idx + 1 < args.ad_times:
            sleep_between(args.ad_between)

    sleep_between(args.close_wait)
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
            f"times={args.times}, panel_wait={args.panel_wait}, ad_wait={args.ad_wait}, "
            f"reward_wait={args.reward_wait}, between={args.between}, points={points}"
        )
        return 0
    backend = perform_click(*points["patrol_truck"], args.backend, bounds)
    print(f"patrol ad from-home: clicked patrol truck via {backend}", flush=True)
    sleep_between(args.panel_wait)
    backend = run_repeated_click_flow(
        points=points,
        bounds=bounds,
        backend_name=args.backend,
        count=args.times,
        between=args.between,
        steps=(
            ("quick_patrol", "patrol ad {index}/{count}: clicked watch-ad via {backend}", args.ad_wait),
            ("ad_close_top", "patrol ad {index}/{count}: clicked ad-close via {backend}", args.reward_wait),
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
            f"times={args.times}, reward_wait={args.reward_wait}, "
            f"between={args.between}, points={points}"
        )
        return 0
    backend = run_repeated_click_flow(
        points=points,
        bounds=bounds,
        backend_name=args.backend,
        count=args.times,
        between=args.between,
        steps=(
            ("quick_patrol", "quick patrol {index}/{count}: clicked quick-patrol via {backend}", args.reward_wait),
            ("reward_dismiss", "quick patrol {index}/{count}: clicked reward-dismiss via {backend}", 0),
        ),
    )
    print(f"patrol quick batch complete: attempted {args.times} via {backend}")
    return 0


def command_mail_claim(args: argparse.Namespace) -> int:
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "right_menu",
        "mail_entry",
        "mail_claim_all",
        "mail_reward_popup_dismiss",
        "mail_close",
        "mail_menu_dismiss",
    )
    if args.dry_run:
        print(
            "mail claim dry-run: "
            f"menu_wait={args.menu_wait}, open_wait={args.open_wait}, "
            f"reward_wait={args.reward_wait}, points={points}"
        )
        return 0
    backend = perform_click(*points["right_menu"], args.backend, bounds)
    set_phase_state(args, "mail_menu_opened")
    print(f"mail claim: clicked top-right menu via {backend}", flush=True)
    sleep_between(args.menu_wait)
    backend = perform_click(*points["mail_entry"], args.backend, bounds)
    set_phase_state(args, "mail_opened")
    print(f"mail claim: clicked mail entry via {backend}", flush=True)
    sleep_between(args.open_wait)
    backend = perform_click(*points["mail_claim_all"], args.backend, bounds)
    print(f"mail claim: clicked one-click claim via {backend}", flush=True)
    sleep_between(args.reward_wait)
    backend = perform_dismiss_click(*points["mail_reward_popup_dismiss"], args.backend, bounds)
    print(f"mail claim: clicked reward-dismiss via {backend}", flush=True)
    backend = perform_click(*points["mail_close"], args.backend, bounds)
    print(f"mail claim: clicked close via {backend}", flush=True)
    sleep_between(args.menu_wait)
    backend = perform_click(*points["mail_menu_dismiss"], args.backend, bounds)
    print(f"mail claim complete: dismissed menu via {backend}")
    return 0


def command_calendar_claim(args: argparse.Namespace) -> int:
    """Claim the calendar's visible free gift and return to the home page."""
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "calendar_top",
        "calendar_gift",
        "reward_dismiss",
        "calendar_close",
    )
    if args.dry_run:
        print(
            "calendar claim dry-run: "
            f"open_wait={args.open_wait}, reward_wait={args.reward_wait}, points={points}"
        )
        return 0

    backend = perform_click(*points["calendar_top"], args.backend, bounds)
    set_phase_state(args, "calendar_opened")
    print(f"calendar claim: opened calendar via {backend}", flush=True)
    sleep_between(args.open_wait)
    backend = perform_click(*points["calendar_gift"], args.backend, bounds)
    print(f"calendar claim: clicked visible free gift via {backend}", flush=True)
    sleep_between(args.reward_wait)
    backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
    print(f"calendar claim: dismissed reward via {backend}", flush=True)
    backend = perform_click(*points["calendar_close"], args.backend, bounds)
    print(f"calendar claim complete: closed calendar via {backend}")
    return 0


def command_welfare_claim(args: argparse.Namespace) -> int:
    """Claim the automatic free welfare popup and return without visiting recharge tabs."""
    bounds = prepare_command_bounds(args)
    points = scaled_points(bounds, "welfare_cluster", "welfare_reward_popup_dismiss", "back_bottom_left")
    if args.dry_run:
        print(
            "welfare claim dry-run: "
            f"open_wait={args.open_wait}, reward_wait={args.reward_wait}, points={points}"
        )
        return 0

    backend = perform_click(*points["welfare_cluster"], args.backend, bounds)
    set_phase_state(args, "welfare_opened")
    print(f"welfare claim: opened welfare cluster via {backend}", flush=True)
    sleep_between(args.open_wait)
    backend = perform_dismiss_click(*points["welfare_reward_popup_dismiss"], args.backend, bounds)
    print(f"welfare claim: dismissed automatic free reward via {backend}", flush=True)
    sleep_between(args.reward_wait)
    backend = perform_click(*points["back_bottom_left"], args.backend, bounds)
    print(f"welfare claim complete: returned without visiting recharge tabs via {backend}")
    return 0


def command_journey_resource_claim(args: argparse.Namespace) -> int:
    """Open Journey and collect the verified gold and wood resource bubbles once each."""
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "journey_tab",
        "journey_gold_claim",
        "journey_wood_claim",
        "reward_dismiss",
    )
    if args.dry_run:
        print(f"journey resource claim dry-run: points={points}")
        return 0

    backend = perform_click(*points["journey_tab"], args.backend, bounds)
    print(f"journey resource claim: opened journey tab via {backend}", flush=True)
    backend = perform_click(*points["journey_gold_claim"], args.backend, bounds)
    print(f"journey resource claim: collected gold resource via {backend}", flush=True)
    backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
    print(f"journey resource claim: dismissed gold reward popup via {backend}", flush=True)
    backend = perform_click(*points["journey_wood_claim"], args.backend, bounds)
    print(f"journey resource claim: collected wood resource via {backend}", flush=True)
    backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
    print(f"journey resource claim: dismissed wood reward popup via {backend}")
    return 0


def recover_phase(progress: PhaseProgress, args: argparse.Namespace) -> None:
    """Return a failed composite phase to its known safe boundary when possible."""
    if progress.state == "not_entered" or args.dry_run:
        return
    bounds = args.mock_bounds
    actions_by_state = {
        "patrol_opened": ("patrol_close",),
        "calendar_opened": ("calendar_close",),
        "welfare_opened": ("back_bottom_left",),
        "mail_menu_opened": ("mail_menu_dismiss",),
        "mail_opened": ("mail_close", "mail_menu_dismiss"),
        "legion_opened": (),
        "legion_daily_cut_opened": ("legion_modal_close",),
        "legion_foreign_challenge_opened": ("legion_foreign_challenge_back",),
        "legion_rewards_opened": ("legion_reward_panel_close", "legion_foreign_challenge_back"),
    }
    try:
        actions = actions_by_state.get(progress.state)
        if actions is None:
            raise PhaseRecoveryError(f"{progress.name} has no safe recovery from {progress.state}")
        ensure_unchanged_game_window(bounds)
        for action in actions:
            x, y = scale_point(ACTIONS[action], bounds)
            perform_click(x, y, args.backend, bounds)
    except ClickError as exc:
        raise PhaseRecoveryError(f"{progress.name} recovery failed from {progress.state}: {exc}") from exc


def run_daily_phase(
    name: str,
    handler: Callable[[argparse.Namespace], int],
    args: argparse.Namespace,
) -> PhaseResult:
    progress = PhaseProgress(name)
    args.phase_progress = progress
    try:
        handler(args)
        return PhaseResult(name, "completed")
    except ClickDeliveryError as exc:
        recover_phase(progress, args)
        return PhaseResult(name, "recovered_failure", str(exc))


def print_daily_summary(results: list[PhaseResult]) -> None:
    status = "partial" if any(result.status == "recovered_failure" for result in results) else "complete"
    rendered = ", ".join(
        f"{result.name}={result.status}" + (f" ({result.error})" if result.error else "")
        for result in results
    )
    print(f"daily rewards {status}: {rendered}")


def command_daily_rewards(args: argparse.Namespace) -> int:
    """Run patrol, calendar, welfare, mail, and legion rewards against one checked window."""
    if args.mock_bounds:
        bounds = get_bounds(args)
        validate_bounds(bounds, allow_mock=True)
    else:
        snapshot = front_window_snapshot()
        status = classify_snapshot(snapshot)
        if status != "game_ready":
            raise WindowStateError(
                "game window is not ready: "
                f"{status} title={snapshot.get('title')!r} "
                f"app={snapshot.get('app')!r} bundle={snapshot.get('bundle')!r}"
            )
        bounds = fit_game_window() if args.fit else ensure_valid_game_bounds(get_bounds(args))
        validate_bounds(bounds, allow_mock=False)

    phase_values = {
        **vars(args),
        "mock_bounds": bounds,
        "fit": False,
        "quick_times": 3,
        "ad_times": 5,
        "panel_wait": 2.0,
        "claim_wait": 2.0,
        "dismiss_wait": 1.0,
        "quick_reward_wait": 4.5,
        "quick_between": 2.0,
        "ad_wait": 35.0,
        "ad_close_wait": 1.2,
        "ad_reward_wait": 1.0,
        "ad_between": 2.0,
        "close_wait": 1.5,
        "menu_wait": 1.0,
        "open_wait": 1.0,
        "reward_wait": 1.2,
        "sweep_times": 2,
        "confirm_wait": 0.8,
        "sweep_reward_wait": 1.2,
        "sweep_between": 0.6,
        "reward_page_wait": 4.0,
    }
    phase_args = argparse.Namespace(**phase_values)

    phases: tuple[tuple[str, Callable[[argparse.Namespace], int]], ...] = (
        ("patrol", command_patrol_full_from_home),
        ("calendar", command_calendar_claim),
        ("welfare", command_welfare_claim),
        ("mail", command_mail_claim),
        ("legion", command_legion_daily_rewards),
        ("journey", command_journey_resource_claim),
    )
    from_step = getattr(args, "from_step", 1)
    start_index = from_step - 1
    results: list[PhaseResult] = [
        PhaseResult(name, "skipped") for name, _ in phases[:start_index]
    ]
    for index, (name, handler) in enumerate(phases[start_index:], start=start_index):
        print(f"daily rewards: starting step {index + 1} {name}", flush=True)
        try:
            results.append(run_daily_phase(name, handler, phase_args))
        except ClickError as exc:
            results.append(PhaseResult(name, "fatal_failure", str(exc)))
            results.extend(PhaseResult(skipped_name, "skipped") for skipped_name, _ in phases[index + 1 :])
            print_daily_summary(results)
            raise
    print_daily_summary(results)
    return 0


def command_legion_daily_rewards(args: argparse.Namespace) -> int:
    """Run the verified daily-cut, foreign-sweep, and legion-reward sequence."""
    if args.sweep_times < 1:
        raise ClickError("--sweep-times must be >= 1")
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "legion_tab",
        "legion_daily_cut",
        "legion_cut_once",
        "reward_dismiss",
        "legion_modal_close",
    )
    if args.dry_run:
        print(
            "legion daily rewards dry-run: "
            f"sweep_times={args.sweep_times}, confirm_wait={args.confirm_wait}, "
            f"sweep_reward_wait={args.sweep_reward_wait}, sweep_between={args.sweep_between}, "
            f"reward_page_wait={args.reward_page_wait}, reward_wait={args.reward_wait}, "
            f"points={points}"
        )
        command_legion_reward_claims(
            argparse.Namespace(
                mock_bounds=bounds,
                backend=args.backend,
                dry_run=True,
                sweep_times=args.sweep_times,
                confirm_wait=args.confirm_wait,
                sweep_reward_wait=args.sweep_reward_wait,
                sweep_between=args.sweep_between,
                reward_page_wait=args.reward_page_wait,
                reward_wait=args.reward_wait,
            )
        )
        return 0

    backend = perform_click(*points["legion_tab"], args.backend, bounds)
    set_phase_state(args, "legion_opened")
    print(f"legion daily rewards: clicked legion tab via {backend}", flush=True)
    backend = perform_click(*points["legion_daily_cut"], args.backend, bounds)
    set_phase_state(args, "legion_daily_cut_opened")
    print(f"legion daily rewards: opened daily cut via {backend}", flush=True)
    backend = perform_click(*points["legion_cut_once"], args.backend, bounds)
    print(f"legion daily rewards: clicked daily cut once via {backend}", flush=True)
    backend = perform_dismiss_click(*points["reward_dismiss"], args.backend, bounds)
    print(f"legion daily rewards: dismissed daily-cut reward info via {backend}", flush=True)
    backend = perform_click(*points["legion_modal_close"], args.backend, bounds)
    print(f"legion daily rewards: closed daily-cut modal via {backend}", flush=True)

    command_legion_reward_claims(
        argparse.Namespace(
            mock_bounds=bounds,
            backend=args.backend,
            dry_run=False,
            sweep_times=args.sweep_times,
            confirm_wait=args.confirm_wait,
            sweep_reward_wait=args.sweep_reward_wait,
            sweep_between=args.sweep_between,
            reward_page_wait=args.reward_page_wait,
            reward_wait=args.reward_wait,
            phase_progress=getattr(args, "phase_progress", None),
        )
    )
    print("legion daily rewards complete: attempted daily cut and full foreign-challenge rewards")
    return 0


def command_legion_reward_claims(args: argparse.Namespace) -> int:
    if args.sweep_times < 1:
        raise ClickError("--sweep-times must be >= 1")
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "legion_tab",
        "legion_foreign_challenge",
        "legion_sweep",
        "legion_sweep_confirm",
        "legion_reward_popup_dismiss",
        "legion_reward_left",
        "legion_reward_claim_top",
        "reward_dismiss",
        "legion_personal_reward_tab",
        "legion_personal_reward_claim_top",
        "legion_reward_panel_close",
        "legion_foreign_challenge_back",
    )
    if args.dry_run:
        print(
            "legion reward claims dry-run: "
            f"sweep_times={args.sweep_times}, confirm_wait={args.confirm_wait}, "
            f"sweep_reward_wait={args.sweep_reward_wait}, sweep_between={args.sweep_between}, "
            f"reward_page_wait={args.reward_page_wait}, reward_wait={args.reward_wait}, "
            f"points={points}"
        )
        return 0
    backend = perform_click(*points["legion_tab"], args.backend, bounds)
    set_phase_state(args, "legion_opened")
    print(f"legion reward claims: clicked legion tab via {backend}", flush=True)
    backend = perform_click(*points["legion_foreign_challenge"], args.backend, bounds)
    set_phase_state(args, "legion_foreign_challenge_opened")
    print(f"legion reward claims: clicked foreign challenge via {backend}", flush=True)
    run_repeated_click_flow(
        points={
            "sweep": points["legion_sweep"],
            "confirm": points["legion_sweep_confirm"],
            "dismiss": points["legion_reward_popup_dismiss"],
        },
        bounds=bounds,
        backend_name=args.backend,
        count=args.sweep_times,
        between=args.sweep_between,
        steps=(
            ("sweep", "legion reward claims sweep {index}/{count}: clicked sweep via {backend}", args.confirm_wait),
            ("confirm", "legion reward claims sweep {index}/{count}: clicked confirm via {backend}", args.sweep_reward_wait),
            ("dismiss", "legion reward claims sweep {index}/{count}: clicked reward-dismiss via {backend}", 0),
        ),
    )
    for action, message, wait in (
        ("legion_reward_left", "clicked rewards tab", args.reward_page_wait),
        ("legion_reward_claim_top", "clicked legion all-rewards claim", 0),
        ("reward_dismiss", "dismissed legion reward", 0),
        ("legion_personal_reward_tab", "clicked personal rewards tab", 0),
        ("legion_personal_reward_claim_top", "clicked personal all-rewards claim", 0),
        ("reward_dismiss", "dismissed personal reward", 0),
        ("legion_reward_panel_close", "closed rewards panel", 0),
        ("legion_foreign_challenge_back", "returned to legion", 0),
    ):
        click = perform_dismiss_click if action == "reward_dismiss" else perform_click
        backend = click(*points[action], args.backend, bounds)
        if action == "legion_reward_left":
            set_phase_state(args, "legion_rewards_opened")
        print(f"legion reward claims: {message} via {backend}", flush=True)
        if wait:
            sleep_between(wait)
    print(f"legion reward claims complete: attempted full foreign-challenge route via {backend}")
    return 0


def command_legion_sweep_batch(args: argparse.Namespace) -> int:
    if args.times < 1:
        raise ClickError("--times must be >= 1")
    bounds = prepare_command_bounds(args)
    points = scaled_points(
        bounds,
        "legion_sweep",
        "legion_sweep_confirm",
        "legion_reward_popup_dismiss",
    )
    points = {
        "sweep": points["legion_sweep"],
        "confirm": points["legion_sweep_confirm"],
        "dismiss": points["legion_reward_popup_dismiss"],
    }
    if args.dry_run:
        print(
            "legion sweep batch dry-run: "
            f"times={args.times}, confirm_wait={args.confirm_wait}, "
            f"reward_wait={args.reward_wait}, between={args.between}, points={points}"
        )
        return 0
    backend = run_repeated_click_flow(
        points=points,
        bounds=bounds,
        backend_name=args.backend,
        count=args.times,
        between=args.between,
        steps=(
            ("sweep", "legion sweep {index}/{count}: clicked sweep via {backend}", args.confirm_wait),
            ("confirm", "legion sweep {index}/{count}: clicked confirm via {backend}", args.reward_wait),
            ("dismiss", "legion sweep {index}/{count}: clicked reward-dismiss via {backend}", 0),
        ),
    )
    print(f"legion sweep batch complete: attempted {args.times} via {backend}")
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
    patrol_ads_parser.add_argument("--ad-wait", type=non_negative_float, default=35.0)
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
    patrol_full_parser.add_argument("--ad-wait", type=non_negative_float, default=35.0)
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
    patrol_ads_home_parser.add_argument("--ad-wait", type=non_negative_float, default=35.0)
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
        help="run the free Battlefield Contest and Element Trial route from the base tab",
    )
    base_parser.add_argument("--battle-times", type=int, default=5)
    base_parser.add_argument("--backend", choices=CLICK_BACKENDS, default="auto")
    base_parser.add_argument("--skip-scroll", action="store_true", help="use after Computer Use has scrolled to the training hall bottom")
    base_parser.add_argument("--dry-run", action="store_true", help="print planned points without clicking or sleeping")
    base_parser.set_defaults(func=command_base_training_hall)

    daily_parser = sub.add_parser(
        "daily-rewards",
        help="run patrol, calendar, welfare, mail, legion, and Journey daily rewards with one checked game window",
    )
    daily_parser.add_argument("--fit", action=argparse.BooleanOptionalAction, default=True)
    daily_parser.add_argument(
        "--from-step",
        type=int,
        choices=range(1, 7),
        default=1,
        metavar="N",
        help="resume at phase 1=patrol, 2=calendar, 3=welfare, 4=mail, 5=legion, or 6=journey",
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
