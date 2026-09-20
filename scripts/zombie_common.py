"""Shared safety boundary and input primitives for the click helper."""

from __future__ import annotations

import argparse
import builtins
import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, Tuple

from .zombie_actions import ACTIONS, REWARD_ACTION_NAMES, Action

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
POST_CLICK_WAIT_MIN = 0.8
POST_CLICK_WAIT_MAX = 1.0
MIN_WAIT_SECONDS = 0.5
REWARD_POST_ACTION_MIN_SECONDS = 1.85
CLICK_HOLD_SECONDS = 0.08
CLICK_HOLD_MILLISECONDS = 80
WINDOW_FOCUS_TIMEOUT_SECONDS = 8.0
POST_AD_READY_TIMEOUT_SECONDS = 8.0
POST_AD_READY_POLL_SECONDS = 0.4
SESSION_AUDIT_EVERY_OPERATIONS = 3
SESSION_AUDIT_MAX_AGE_SECONDS = 2.0
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
#include <string.h>
#include <unistd.h>
int main(int argc, char **argv) {
  if (argc == 6 && strcmp(argv[1], "drag") == 0) {
    CGPoint start = CGPointMake(atof(argv[2]), atof(argv[3]));
    CGPoint end = CGPointMake(atof(argv[4]), atof(argv[5]));
    CGEventSourceRef src = CGEventSourceCreate(kCGEventSourceStateHIDSystemState);
    if (!src) return 3;
    CGEventRef move = CGEventCreateMouseEvent(src, kCGEventMouseMoved, start, kCGMouseButtonLeft);
    CGEventRef down = CGEventCreateMouseEvent(src, kCGEventLeftMouseDown, start, kCGMouseButtonLeft);
    CGEventRef up = CGEventCreateMouseEvent(src, kCGEventLeftMouseUp, end, kCGMouseButtonLeft);
    if (!move || !down || !up) return 4;
    CGEventPost(kCGHIDEventTap, move);
    CGEventPost(kCGHIDEventTap, down);
    usleep(80000);
    for (int step = 1; step <= 12; step++) {
      double fraction = (double)step / 12.0;
      CGPoint point = CGPointMake(
        start.x + (end.x - start.x) * fraction,
        start.y + (end.y - start.y) * fraction
      );
      CGEventRef drag = CGEventCreateMouseEvent(src, kCGEventLeftMouseDragged, point, kCGMouseButtonLeft);
      if (!drag) return 4;
      CGEventPost(kCGHIDEventTap, drag);
      CFRelease(drag);
      usleep(16000);
    }
    CGEventPost(kCGHIDEventTap, up);
    CFRelease(move);
    CFRelease(down);
    CFRelease(up);
    CFRelease(src);
    return 0;
  }
  if (argc == 5 && strcmp(argv[1], "scroll") == 0) {
    double x = atof(argv[2]);
    double y = atof(argv[3]);
    int lines = atoi(argv[4]);
    CGEventSourceRef src = CGEventSourceCreate(kCGEventSourceStateHIDSystemState);
    if (!src) return 3;
    CGEventRef move = CGEventCreateMouseEvent(src, kCGEventMouseMoved, CGPointMake(x, y), kCGMouseButtonLeft);
    CGEventRef scroll = CGEventCreateScrollWheelEvent(src, kCGScrollEventUnitLine, 1, lines);
    if (!move || !scroll) return 4;
    CGEventPost(kCGHIDEventTap, move);
    usleep(80000);
    CGEventPost(kCGHIDEventTap, scroll);
    CFRelease(move);
    CFRelease(scroll);
    CFRelease(src);
    return 0;
  }
  if (argc != 3) { fprintf(stderr, "usage: zombie_cgclick x y | zombie_cgclick scroll x y lines | zombie_cgclick drag x1 y1 x2 y2\n"); return 2; }
  CGEventSourceRef src = CGEventSourceCreate(kCGEventSourceStateHIDSystemState);
  if (!src) return 3;
  double x = atof(argv[1]);
  double y = atof(argv[2]);
  CGPoint p = CGPointMake(x, y);
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


def print(*values, sep: str = " ", end: str = "\n", file=None, flush: bool = False) -> None:
    """Print console output with a local HH:MM:SS prefix on every non-empty line."""
    target = sys.stdout if file is None else file
    message = sep.join(str(value) for value in values)
    lines = message.splitlines() or [""]
    timestamped = "\n".join(
        f"{datetime.now():%H:%M:%S} {line}" if line else ""
        for line in lines
    )
    builtins.print(timestamped, end=end, file=target, flush=flush)


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
class InputSession:
    """Per-command window proof that permits a short run of safe inputs."""

    id: str
    bounds: Bounds | None = None
    operations_since_audit: int = 0
    last_audit_at: float = 0.0


_input_session: InputSession | None = None


def start_input_session() -> None:
    """Enable short-lived verification reuse for one CLI command."""
    global _input_session
    _input_session = InputSession(id=str(os.getpid()))
    print(f"input-session: start id={_input_session.id}", flush=True)


def format_bounds(bounds: Bounds | None) -> str:
    if bounds is None:
        return "none"
    return (
        f"({bounds.app_name},{bounds.bundle_id},{bounds.x},{bounds.y},"
        f"{bounds.width},{bounds.height})"
    )


def bind_input_session(bounds: Bounds) -> None:
    """Record a just-focused, calibrated game window for the active command."""
    if _input_session is None:
        return
    _input_session.bounds = bounds
    _input_session.operations_since_audit = 0
    _input_session.last_audit_at = time.monotonic()
    print(
        f"input-session: bind id={_input_session.id} bounds={format_bounds(bounds)}",
        flush=True,
    )


def end_input_session() -> None:
    """Discard command-local window proof so it cannot leak to a later run."""
    global _input_session
    if _input_session is not None:
        print(f"input-session: end id={_input_session.id}", flush=True)
    _input_session = None


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
    bind_input_session(bounds)
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


def scroll_cgclick_bin(x: int, y: int, lines: int) -> bool:
    if not ensure_cgclick():
        return False
    assert CGCLICK_BIN is not None
    subprocess.run([CGCLICK_BIN, "scroll", str(x), str(y), str(lines)], check=True)
    return True


def drag_cgclick_bin(x1: int, y1: int, x2: int, y2: int) -> bool:
    if not ensure_cgclick():
        return False
    assert CGCLICK_BIN is not None
    subprocess.run([CGCLICK_BIN, "drag", str(x1), str(y1), str(x2), str(y2)], check=True)
    return True


def click_system_events(x: int, y: int) -> bool:
    # System Events exposes only an atomic `click at` action. Route its legacy
    # selector to cgclick so every real delivery has move/down/hold/up semantics.
    return click_cgclick_bin(x, y)


def wait_after_click() -> None:
    time.sleep(random.uniform(POST_CLICK_WAIT_MIN, POST_CLICK_WAIT_MAX))


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


def log_operation(kind: str, status: str, details: str) -> None:
    """Write an auditable result for one physical input operation."""
    print(f"operation: {kind} status={status} {details}", flush=True)


def input_preflight(expected_bounds: Bounds, *, retry: bool = False) -> tuple[str, float, str]:
    """Use a bounded session audit when safe, otherwise run the full guard."""
    started_at = time.monotonic()
    session = _input_session
    if session is None:
        session_id = "none"
        session_state = "missing"
        session_age_ms = -1.0
        bound_bounds = None
    else:
        session_id = session.id
        bound_bounds = session.bounds
        session_age_ms = max(0.0, (started_at - session.last_audit_at) * 1000)
        if session.bounds is None:
            session_state = "unbound"
        elif session.bounds == expected_bounds:
            session_state = "match"
        else:
            session_state = "bounds_mismatch"
    diagnostic = (
        f"session_id={session_id} session_state={session_state} "
        f"session_age_ms={session_age_ms:.1f} "
        f"expected_bounds={format_bounds(expected_bounds)} "
        f"bound_bounds={format_bounds(bound_bounds)}"
    )
    if (
        not retry
        and session is not None
        and session.bounds == expected_bounds
        and session.operations_since_audit < SESSION_AUDIT_EVERY_OPERATIONS
        and started_at - session.last_audit_at < SESSION_AUDIT_MAX_AGE_SECONDS
    ):
        session.operations_since_audit += 1
        return "session", (time.monotonic() - started_at) * 1000, diagnostic

    mode = "full" if retry or session is None or session.bounds != expected_bounds else "audit"
    try:
        if mode == "full":
            focus_game_window(expected_bounds)
        ensure_unchanged_game_window(expected_bounds)
    except WindowStateError:
        # A short-session check discovered a focus loss. Re-establish the
        # calibrated game window before allowing the one normal retry path.
        if mode != "audit":
            raise
        focus_game_window(expected_bounds)
        ensure_unchanged_game_window(expected_bounds)
        mode = "recovery"

    if session is not None and session.bounds == expected_bounds:
        session.operations_since_audit = 1
        session.last_audit_at = time.monotonic()
    return mode, (time.monotonic() - started_at) * 1000, diagnostic


def perform_click(
    x: int,
    y: int,
    backend: str = "auto",
    expected_bounds: Bounds | None = None,
    wait_after: bool = True,
    post_reward_wait_seconds: float | None = None,
) -> str:
    if expected_bounds is None:
        raise ClickDeliveryError("real clicks require calibrated game-window bounds")
    failures = []
    for attempt_index in range(2):
        mode, preflight_ms, session_diagnostic = input_preflight(
            expected_bounds,
            retry=attempt_index > 0,
        )
        for candidate in click_backend_candidates(backend):
            delivery_started_at = time.monotonic()
            clicked, reason = try_click_backend(candidate, x, y)
            delivery_ms = (time.monotonic() - delivery_started_at) * 1000
            if clicked:
                reward_wait_detail = (
                    f" post_reward_wait_ms={post_reward_wait_seconds * 1000:.1f}"
                    if post_reward_wait_seconds is not None
                    else ""
                )
                log_operation(
                    "click",
                    "success",
                    f"backend={candidate} point=({x},{y}) mode={mode} {session_diagnostic} "
                    f"preflight_ms={preflight_ms:.1f} deliver_ms={delivery_ms:.1f}{reward_wait_detail}",
                )
                if post_reward_wait_seconds is not None:
                    reward_wait_started_at = time.monotonic()
                    time.sleep(post_reward_wait_seconds)
                    log_operation(
                        "reward-wait",
                        "success",
                        f"minimum_ms={post_reward_wait_seconds * 1000:.1f} "
                        f"post_reward_wait_actual_ms={(time.monotonic() - reward_wait_started_at) * 1000:.1f}",
                    )
                elif wait_after:
                    wait_after_click()
                return candidate
            log_operation(
                "click",
                "failed",
                f"backend={candidate} point=({x},{y}) mode={mode} {session_diagnostic} "
                f"preflight_ms={preflight_ms:.1f} deliver_ms={delivery_ms:.1f} reason={reason}",
            )
            failures.append(f"{candidate}: {reason}")
    raise ClickDeliveryError("click backend failed: " + "; ".join(failures))


def perform_dismiss_click(
    x: int,
    y: int,
    backend: str,
    expected_bounds: Bounds,
) -> str:
    """Dismiss a reward popup without adding a fixed post-dismiss wait."""
    return perform_click(x, y, backend, expected_bounds, False)


def perform_reward_click(
    x: int,
    y: int,
    backend: str,
    expected_bounds: Bounds,
) -> str:
    """Claim a reward and wait project-wide before any later physical input."""
    return perform_click(
        x,
        y,
        backend,
        expected_bounds,
        False,
        REWARD_POST_ACTION_MIN_SECONDS,
    )


def perform_drag(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    expected_bounds: Bounds | None = None,
) -> None:
    """Deliver one calibrated CoreGraphics drag and log its result."""
    if expected_bounds is None:
        raise ClickDeliveryError("real drags require calibrated game-window bounds")
    mode, preflight_ms, session_diagnostic = input_preflight(expected_bounds)
    delivery_started_at = time.monotonic()
    try:
        delivered = drag_cgclick_bin(x1, y1, x2, y2)
    except Exception as exc:
        reason = str(exc) or exc.__class__.__name__
        log_operation(
            "drag",
            "failed",
            f"backend=cgclick start=({x1},{y1}) end=({x2},{y2}) mode={mode} {session_diagnostic} "
            f"preflight_ms={preflight_ms:.1f} deliver_ms={(time.monotonic() - delivery_started_at) * 1000:.1f} reason={reason}",
        )
        raise ClickDeliveryError(f"drag backend failed: {reason}") from exc
    if not delivered:
        log_operation(
            "drag",
            "failed",
            f"backend=cgclick start=({x1},{y1}) end=({x2},{y2}) mode={mode} {session_diagnostic} "
            f"preflight_ms={preflight_ms:.1f} deliver_ms={(time.monotonic() - delivery_started_at) * 1000:.1f} reason=unavailable",
        )
        raise ClickDeliveryError("drag backend unavailable")
    log_operation(
        "drag",
        "success",
        f"backend=cgclick start=({x1},{y1}) end=({x2},{y2}) mode={mode} {session_diagnostic} "
        f"preflight_ms={preflight_ms:.1f} deliver_ms={(time.monotonic() - delivery_started_at) * 1000:.1f}",
    )


def sleep_between(seconds: float) -> None:
    time.sleep(max(MIN_WAIT_SECONDS, seconds - 0.5))


def run_repeated_click_flow(
    *,
    points: Dict[str, Tuple[int, int]],
    bounds: Bounds,
    backend_name: str,
    count: int,
    between: float,
    reward_actions: frozenset[str] = frozenset(),
    steps: tuple[tuple[str, str, float], ...],
) -> str:
    """Run a repeated action flow and return the backend used by its last click."""
    backend = ""
    for index in range(count):
        for action_name, message, wait in steps:
            click = (
                perform_dismiss_click
                if "dismiss" in action_name
                else perform_reward_click
                if action_name in REWARD_ACTION_NAMES or action_name in reward_actions
                else perform_click
            )
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
