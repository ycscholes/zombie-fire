import importlib.util
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch


SCRIPT = pathlib.Path(__file__).with_name("zombie_click.py")
SPEC = importlib.util.spec_from_file_location("zombie_click", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
zombie_click = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = zombie_click
SPEC.loader.exec_module(zombie_click)


class FocusEligibilityTests(unittest.TestCase):
    @staticmethod
    def game_snapshot(
        title: str,
        *,
        width: int = 508,
        height: int = 949,
    ) -> dict[str, object]:
        return {
            "app": "WeChat",
            "bundle": "com.tencent.xinWeChat",
            "title": title,
            "x": 2,
            "y": 33,
            "width": width,
            "height": height,
        }

    def test_non_operating_commands_do_not_focus(self) -> None:
        for command in ("list", "state", "self-test", "dry-run"):
            with self.subTest(command=command):
                self.assertFalse(zombie_click.command_requires_focus(command))

    def test_operating_commands_focus(self) -> None:
        for command in ("bounds", "fit-window", "click", "seq", "mail-claim"):
            with self.subTest(command=command):
                self.assertTrue(zombie_click.command_requires_focus(command))

    def test_main_focuses_before_dispatching_an_operating_command(self) -> None:
        events: list[str] = []

        def record_focus() -> None:
            events.append("focus")

        def record_dispatch(args: object) -> int:
            events.append("dispatch")
            return 0

        with (
            patch.object(
                zombie_click,
                "focus_game_window_at_start",
                side_effect=record_focus,
            ) as focus,
            patch.object(zombie_click, "command_click", side_effect=record_dispatch) as command_click,
        ):
            self.assertEqual(zombie_click.main(["click", "patrol_truck"]), 0)

        focus.assert_called_once_with()
        command_click.assert_called_once()
        self.assertEqual(events, ["focus", "dispatch"])

    def test_main_does_not_focus_before_dispatching_an_exempt_command(self) -> None:
        with patch.object(zombie_click, "focus_game_window_at_start") as focus:
            self.assertEqual(zombie_click.main(["self-test"]), 0)

        focus.assert_not_called()

    def test_main_mock_patrol_dry_run_does_not_focus(self) -> None:
        with patch.object(zombie_click, "focus_game_window_at_start") as focus:
            self.assertEqual(
                zombie_click.main(
                    [
                        "--mock-bounds",
                        "2,33,508,949",
                        "patrol-full-from-home",
                        "--dry-run",
                    ]
                ),
                0,
            )

        focus.assert_not_called()

    def test_auto_backend_uses_cgclick(self) -> None:
        self.assertEqual(zombie_click.click_backend_candidates("auto"), ("cgclick",))

    def test_system_events_click_uses_named_finite_timeout(self) -> None:
        with patch.object(zombie_click.subprocess, "run") as run:
            run.return_value = Mock(returncode=0, stdout="", stderr="")

            self.assertTrue(zombie_click.click_system_events(10, 20))

        self.assertEqual(zombie_click.SYSTEM_EVENTS_CLICK_TIMEOUT_SECONDS, 8.0)
        self.assertEqual(run.call_args.kwargs["timeout"], zombie_click.SYSTEM_EVENTS_CLICK_TIMEOUT_SECONDS)

    def test_auto_does_not_try_system_events_after_cgclick_failure(self) -> None:
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        with (
            patch.object(zombie_click, "ensure_unchanged_game_window"),
            patch.object(zombie_click, "wait_after_click"),
            patch.object(
                zombie_click,
                "try_click_backend",
                return_value=(False, "unavailable"),
            ) as attempt,
        ):
            with self.assertRaisesRegex(zombie_click.ClickError, "cgclick: unavailable"):
                zombie_click.perform_click(10, 20, "auto", bounds)

        self.assertEqual(
            [call.args[0] for call in attempt.call_args_list],
            ["cgclick"],
        )

    def test_system_events_timeout_raises_click_error(self) -> None:
        with patch.object(
            zombie_click.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["osascript"], zombie_click.SYSTEM_EVENTS_CLICK_TIMEOUT_SECONDS),
        ):
            with self.assertRaisesRegex(zombie_click.ClickError, "system-events click timed out"):
                zombie_click.click_system_events(10, 20)

    def test_cgclick_cache_paths_are_stable(self) -> None:
        self.assertEqual(zombie_click.CGCLICK_BIN_PATH.parent, zombie_click.CGCLICK_CACHE_DIR)
        self.assertEqual(zombie_click.CGCLICK_BIN_PATH.name, "zombie_cgclick")

    def test_patrol_ad_waits_before_reward_dismiss(self) -> None:
        args = zombie_click.build_parser().parse_args(
            [
                "patrol-full-from-home",
                "--quick-times",
                "0",
                "--ad-times",
                "1",
                "--no-fit",
                "--panel-wait",
                "0",
                "--claim-wait",
                "0",
                "--dismiss-wait",
                "0",
                "--quick-between",
                "0",
                "--ad-wait",
                "0",
                "--ad-close-wait",
                "1.25",
                "--ad-reward-wait",
                "2.5",
                "--ad-between",
                "0",
                "--close-wait",
                "0",
            ]
        )
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        events: list[object] = []
        with (
            patch.object(zombie_click, "get_bounds", return_value=bounds),
            patch.object(
                zombie_click,
                "front_window_snapshot",
                return_value=self.game_snapshot("向僵尸开炮"),
            ),
            patch.object(
                zombie_click,
                "perform_click",
                side_effect=lambda x, y, *_: (events.append(("click", x, y)), "system-events")[1],
            ) as click,
            patch.object(
                zombie_click,
                "sleep_between",
                side_effect=lambda value: events.append(("sleep", value)),
            ),
            patch.object(
                zombie_click,
                "ensure_game_ready_after_ad",
                side_effect=lambda _: events.append("ready"),
            ),
        ):
            self.assertEqual(zombie_click.command_patrol_full_from_home(args), 0)

        close_wait = events.index(("sleep", 1.25))
        reward_wait = events.index(("sleep", 2.5))
        ready = events.index("ready")
        self.assertLess(close_wait, reward_wait)
        self.assertLess(reward_wait, ready)
        first_reward_dismiss_after_ready = next(
            index
            for index, event in enumerate(events[ready + 1 :], start=ready + 1)
            if event == ("click", *zombie_click.scale_point(zombie_click.ACTIONS["reward_dismiss"], bounds))
        )
        self.assertLess(ready, first_reward_dismiss_after_ready)
        self.assertEqual(click.call_count, 9)

    def test_patrol_ad_readiness_failure_stops_before_reward_dismiss(self) -> None:
        args = zombie_click.build_parser().parse_args(
            [
                "patrol-full-from-home",
                "--quick-times",
                "0",
                "--ad-times",
                "1",
                "--no-fit",
                "--panel-wait",
                "0",
                "--claim-wait",
                "0",
                "--dismiss-wait",
                "0",
                "--quick-between",
                "0",
                "--ad-wait",
                "0",
                "--ad-close-wait",
                "0",
                "--ad-reward-wait",
                "0",
                "--ad-between",
                "0",
                "--close-wait",
                "0",
            ]
        )
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        clicks: list[tuple[int, int]] = []
        with (
            patch.object(zombie_click, "get_bounds", return_value=bounds),
            patch.object(
                zombie_click,
                "front_window_snapshot",
                return_value=self.game_snapshot("向僵尸开炮"),
            ),
            patch.object(
                zombie_click,
                "perform_click",
                side_effect=lambda x, y, *_: (clicks.append((x, y)), "system-events")[1],
            ),
            patch.object(zombie_click, "sleep_between"),
            patch.object(
                zombie_click,
                "ensure_game_ready_after_ad",
                side_effect=zombie_click.ClickError("ad still open"),
            ),
        ):
            with self.assertRaisesRegex(zombie_click.ClickError, "ad still open"):
                zombie_click.command_patrol_full_from_home(args)

        reward_dismiss = zombie_click.scale_point(zombie_click.ACTIONS["reward_dismiss"], bounds)
        ad_close_lower = zombie_click.scale_point(zombie_click.ACTIONS["ad_close_lower"], bounds)
        self.assertEqual(clicks.count(reward_dismiss), 2)
        self.assertNotIn(ad_close_lower, clicks)

    def test_focus_raises_and_accepts_the_game_window(self) -> None:
        with (
            patch.object(
                zombie_click,
                "run_osascript",
                return_value="WeChat\tcom.tencent.xinWeChat\t2\t33\t508\t949",
            ) as osascript,
            patch.object(
                zombie_click,
                "front_window_snapshot",
                return_value=self.game_snapshot("向僵尸开炮"),
            ),
        ):
            self.assertEqual(zombie_click.focus_game_window_at_start().width, 508)

        self.assertIn('perform action "AXRaise"', osascript.call_args.args[0])
        self.assertIn('attribute "AXMain"', osascript.call_args.args[0])

    def test_focus_rejects_a_normal_wechat_window(self) -> None:
        with (
            patch.object(
                zombie_click,
                "run_osascript",
                return_value="WeChat\tcom.tencent.xinWeChat\t2\t33\t508\t949",
            ),
            patch.object(
                zombie_click,
                "front_window_snapshot",
                return_value=self.game_snapshot("微信"),
            ),
        ):
            with self.assertRaisesRegex(zombie_click.ClickError, "did not become frontmost"):
                zombie_click.focus_game_window_at_start()

    def test_focus_accepts_the_game_window_before_a_later_geometry_fit(self) -> None:
        with (
            patch.object(
                zombie_click,
                "run_osascript",
                return_value="WeChat\tcom.tencent.xinWeChat\t2\t33\t690\t600",
            ),
            patch.object(
                zombie_click,
                "front_window_snapshot",
                return_value=self.game_snapshot("向僵尸开炮", width=690, height=600),
            ),
        ):
            bounds = zombie_click.focus_game_window_at_start()

        self.assertEqual((bounds.width, bounds.height), (690, 600))
