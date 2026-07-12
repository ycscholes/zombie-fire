import importlib.util
import pathlib
import sys
import unittest
from unittest.mock import patch


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
