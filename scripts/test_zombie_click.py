import io
import argparse
import importlib.util
import pathlib
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch


SCRIPT = pathlib.Path(__file__).with_name("zombie_click.py")
SPEC = importlib.util.spec_from_file_location("zombie_click", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
zombie_click = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = zombie_click
SPEC.loader.exec_module(zombie_click)


class BaseTrainingHallTests(unittest.TestCase):
    def test_task_compat_does_not_replace_base_scroll_with_entry_wrapper(self) -> None:
        original = zombie_click._base.scroll_to_bottom
        zombie_click._sync_task_compat(zombie_click._base)
        self.assertIs(zombie_click._base.scroll_to_bottom, original)

    def test_scroll_helper_emits_a_coregraphics_scroll_event(self) -> None:
        self.assertIn("CGEventCreateScrollWheelEvent", zombie_click.CGCLICK_SOURCE)
        self.assertIn('strcmp(argv[1], "scroll")', zombie_click.CGCLICK_SOURCE)
        self.assertIn("zombie_cgclick scroll x y lines", zombie_click.CGCLICK_SOURCE)

    def test_scroll_helper_emits_a_drag_gesture_for_canvas_lists(self) -> None:
        self.assertIn("kCGEventLeftMouseDragged", zombie_click.CGCLICK_SOURCE)
        self.assertIn('strcmp(argv[1], "drag")', zombie_click.CGCLICK_SOURCE)
        self.assertIn("step <= 12", zombie_click.CGCLICK_SOURCE)

    def test_base_training_hall_parser_defaults_to_five_battle_sweeps(self) -> None:
        args = zombie_click.build_parser().parse_args(["base-training-hall"])
        self.assertEqual(args.battle_times, 5)

    def test_battlefield_contest_targets_bottom_list_row(self) -> None:
        self.assertEqual((zombie_click.ACTIONS["battle_modal_drag_start"].x, zombie_click.ACTIONS["battle_modal_drag_start"].y), (250, 580))
        self.assertEqual((zombie_click.ACTIONS["battle_modal_drag_end"].x, zombie_click.ACTIONS["battle_modal_drag_end"].y), (250, 330))
        self.assertEqual((zombie_click.ACTIONS["battle_sweep_last"].x, zombie_click.ACTIONS["battle_sweep_last"].y), (375, 578))

    def test_base_training_hall_dry_run_is_registered(self) -> None:
        with patch.object(zombie_click, "focus_game_window_at_start") as focus:
            self.assertEqual(
                zombie_click.main(["--mock-bounds", "2,33,508,949", "base-training-hall", "--dry-run"]),
                0,
            )
        focus.assert_not_called()

    def test_base_training_hall_route_uses_new_base_tasks_then_battle_and_element_trial(self) -> None:
        args = zombie_click.build_parser().parse_args(["base-training-hall", "--battle-times", "2"])
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        events: list[str] = []
        with (
            patch.object(zombie_click, "prepare_command_bounds", return_value=bounds),
            patch.object(zombie_click, "perform_click", side_effect=lambda x, y, *_: (events.append((x, y)), "cgclick")[1]),
            patch.object(zombie_click, "perform_dismiss_click", side_effect=lambda x, y, *_: (events.append((x, y)), "cgclick")[1]),
            patch.object(zombie_click, "sleep_between"),
            patch.object(zombie_click, "scroll_to_bottom", side_effect=lambda *_: events.append("scroll")),
            patch.object(zombie_click._base, "command_base_training_hall_shop", return_value=0) as play_shop,
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(zombie_click.command_base_training_hall(args), 0)

        point = lambda name: zombie_click.scale_point(zombie_click.ACTIONS[name], bounds)
        self.assertEqual(events, [
            point("base_tab"), point("cafeteria"), point("cafeteria_claim"),
            point("training_reward_dismiss"), point("cafeteria_back"), point("training_hall"),
            point("global_rescue_challenge"), point("global_rescue_free"), point("training_reward_dismiss"), point("training_hall_back"),
            "scroll", point("terminal_crisis_challenge"), point("terminal_crisis_sweep"), point("terminal_crisis_confirm"),
            point("training_reward_dismiss"), point("training_hall_back"),
            point("battle_challenge"), point("battle_castle"), point("reward_dismiss"), point("battle_modal_challenge"), "scroll",
            point("battle_sweep_last"), point("reward_dismiss"), point("battle_sweep_last"), point("reward_dismiss"),
            point("battle_modal_close"), point("training_hall_back"),
            point("element_challenge"), point("core_trial"), point("idle_button"), point("idle_claim"), point("reward_dismiss"),
            point("idle_cancel"), point("core_sweep"), point("core_sweep_ten"), point("reward_dismiss"), point("core_trial_back"), point("element_back"), point("training_hall_back"),
        ])
        log = output.getvalue()
        play_shop.assert_called_once()
        for action in (
            "base_tab", "cafeteria", "cafeteria_claim", "training_reward_dismiss", "cafeteria_back", "training_hall",
            "global_rescue_challenge", "global_rescue_free", "training_hall_back", "scroll_to_bottom",
            "terminal_crisis_challenge", "terminal_crisis_sweep", "terminal_crisis_confirm",
            "battle_challenge", "battle_castle",
            "battle_modal_challenge", "battle_modal_scroll_to_bottom", "battle_sweep_last", "reward_dismiss", "battle_modal_close",
            "training_hall_back", "element_challenge", "core_trial", "idle_button", "idle_claim",
            "idle_cancel", "core_sweep", "core_sweep_ten", "core_trial_back", "element_back",
        ):
            self.assertIn(f"base training hall: {action}", log)

    def test_base_training_hall_route_includes_cafeteria_and_training_hall_tasks(self) -> None:
        args = zombie_click.build_parser().parse_args(["base-training-hall", "--battle-times", "1"])
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        events: list[object] = []
        with (
            patch.object(zombie_click, "prepare_command_bounds", return_value=bounds),
            patch.object(zombie_click, "perform_click", side_effect=lambda x, y, *_: (events.append((x, y)), "cgclick")[1]),
            patch.object(zombie_click, "perform_dismiss_click", side_effect=lambda x, y, *_: (events.append((x, y, "dismiss")), "cgclick")[1]),
            patch.object(zombie_click, "sleep_between"),
            patch.object(zombie_click, "scroll_to_bottom", side_effect=lambda *_: events.append("scroll")),
            patch.object(zombie_click._base, "command_base_training_hall_shop", return_value=0) as play_shop,
        ):
            self.assertEqual(zombie_click.command_base_training_hall(args), 0)

        play_shop.assert_called_once()
        point = lambda name: zombie_click.scale_point(zombie_click.ACTIONS[name], bounds)
        self.assertEqual(events[:10], [
            point("base_tab"), point("cafeteria"), point("cafeteria_claim"),
            (point("training_reward_dismiss")[0], point("training_reward_dismiss")[1], "dismiss"),
            point("cafeteria_back"), point("training_hall"),
            point("global_rescue_challenge"), point("global_rescue_free"),
            (point("training_reward_dismiss")[0], point("training_reward_dismiss")[1], "dismiss"),
            point("training_hall_back"),
        ])
        self.assertEqual(events[10:16], [
            "scroll", point("terminal_crisis_challenge"), point("terminal_crisis_sweep"),
            point("terminal_crisis_confirm"),
            (point("training_reward_dismiss")[0], point("training_reward_dismiss")[1], "dismiss"),
            point("training_hall_back"),
        ])


class ShopTrainingHallTests(unittest.TestCase):
    def test_shop_training_hall_parser_is_registered(self) -> None:
        args = zombie_click.build_parser().parse_args(["shop-training-hall"])
        self.assertEqual(args.command, "shop-training-hall")

    def test_shop_training_hall_route_claims_resource_and_special_pack_gold(self) -> None:
        args = zombie_click.build_parser().parse_args(["shop-training-hall"])
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        events: list[object] = []
        with (
            patch.object(zombie_click, "prepare_command_bounds", return_value=bounds),
            patch.object(
                zombie_click,
                "perform_click",
                side_effect=lambda x, y, *_: (events.append((x, y)), "cgclick")[1],
            ),
            patch.object(
                zombie_click,
                "perform_dismiss_click",
                side_effect=lambda x, y, *_: (events.append((x, y, "dismiss")), "cgclick")[1],
            ),
            patch.object(zombie_click._shop, "_base_scroll_to_bottom", side_effect=lambda *_: events.append("scroll")),
            patch.object(zombie_click, "sleep_between"),
        ):
            self.assertEqual(zombie_click.command_shop_training_hall(args), 0)

        point = lambda name: zombie_click.scale_point(zombie_click.ACTIONS[name], bounds)
        self.assertEqual(
            events,
            [
                point("shop_tab"), point("shop_resource_tab"), "scroll", "scroll", point("shop_resource_gold600_free"),
                (point("reward_dismiss")[0], point("reward_dismiss")[1], "dismiss"),
                point("shop_special_pack_tab"), point("shop_gold_free"),
                (point("reward_dismiss")[0], point("reward_dismiss")[1], "dismiss"),
            ],
        )

    def test_shop_resource_scroll_and_gold600_coordinates_are_calibrated(self) -> None:
        self.assertEqual(
            (zombie_click.ACTIONS["shop_resource_drag_start"].x, zombie_click.ACTIONS["shop_resource_drag_start"].y),
            (252, 760),
        )
        self.assertEqual(
            (zombie_click.ACTIONS["shop_resource_drag_end"].x, zombie_click.ACTIONS["shop_resource_drag_end"].y),
            (252, 120),
        )
        self.assertEqual(
            (zombie_click.ACTIONS["shop_resource_gold600_free"].x, zombie_click.ACTIONS["shop_resource_gold600_free"].y),
            (255, 605),
        )


class BaseTrainingHallShopTests(unittest.TestCase):
    def test_play_shop_parser_is_registered(self) -> None:
        args = zombie_click.build_parser().parse_args(["base-training-hall-shop"])
        self.assertEqual(args.command, "base-training-hall-shop")

    def test_play_shop_route_starts_in_training_hall_and_completes_four_purchases(self) -> None:
        args = zombie_click.build_parser().parse_args(["base-training-hall-shop"])
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        events: list[object] = []
        with (
            patch.object(zombie_click, "prepare_command_bounds", return_value=bounds),
            patch.object(zombie_click, "perform_click", side_effect=lambda x, y, *_: (events.append((x, y)), "cgclick")[1]),
            patch.object(zombie_click, "perform_dismiss_click", side_effect=lambda x, y, *_: (events.append((x, y, "dismiss")), "cgclick")[1]),
            patch.object(zombie_click, "scroll_to_bottom", side_effect=lambda _args, *names: events.append(("drag", *names))),
            patch.object(zombie_click, "sleep_between"),
        ):
            self.assertEqual(zombie_click.command_base_training_hall_shop(args), 0)

        point = lambda name: zombie_click.scale_point(zombie_click.ACTIONS[name], bounds)
        dismiss = lambda name: (point(name)[0], point(name)[1], "dismiss")
        self.assertEqual(events, [
            point("play_shop"),
            point("play_shop_enhancer"), point("play_shop_max"), point("play_shop_buy"),
            dismiss("play_shop_reward_dismiss"), point("play_shop_modal_close"),
            point("play_shop_battle_tab"), ("drag", "play_shop_battle_drag_start", "play_shop_battle_drag_end"),
            point("play_shop_gun_blueprint"), point("play_shop_max"), point("play_shop_buy"),
            dismiss("play_shop_reward_dismiss"), point("play_shop_modal_close"),
            ("drag", "play_shop_tabs_drag_start", "play_shop_tabs_drag_end"), point("play_shop_element_tab"),
            point("play_shop_base_material"), point("play_shop_max"), point("play_shop_buy"),
            dismiss("play_shop_reward_dismiss"), point("play_shop_modal_close"),
            point("play_shop_legion_tab"), point("play_shop_skill_manual"), point("play_shop_max"),
            point("play_shop_buy"), dismiss("play_shop_reward_dismiss"), point("play_shop_modal_close"),
            point("play_shop_close"),
        ])

    def test_play_shop_dry_run_does_not_scroll_or_click(self) -> None:
        with (
            patch.object(zombie_click, "focus_game_window_at_start") as focus,
            patch.object(zombie_click, "perform_click") as click,
            patch.object(zombie_click, "scroll_to_bottom") as drag,
        ):
            self.assertEqual(
                zombie_click.main(["--mock-bounds", "2,33,508,949", "base-training-hall-shop", "--dry-run"]),
                0,
            )
        focus.assert_not_called()
        click.assert_not_called()
        drag.assert_not_called()

    def test_play_shop_coordinates_match_the_verified_content_space(self) -> None:
        expected = {
            "play_shop": (407, 145),
            "play_shop_enhancer": (358, 513),
            "play_shop_battle_tab": (215, 798),
            "play_shop_gun_blueprint": (358, 641),
            "play_shop_tabs_drag_start": (345, 798),
            "play_shop_tabs_drag_end": (145, 798),
            "play_shop_element_tab": (280, 798),
            "play_shop_base_material": (358, 644),
            "play_shop_max": (345, 566),
            "play_shop_buy": (252, 616),
            "play_shop_modal_close": (401, 350),
            "play_shop_close": (426, 214),
        }
        for name, point in expected.items():
            self.assertEqual((zombie_click.ACTIONS[name].x, zombie_click.ACTIONS[name].y), point, name)
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        self.assertEqual(zombie_click.scale_point(zombie_click.ACTIONS["play_shop_enhancer"], bounds), (360, 546))
        self.assertEqual((zombie_click.ACTIONS["play_shop_battle_drag_start"].x, zombie_click.ACTIONS["play_shop_battle_drag_start"].y), (252, 733))
        self.assertEqual((zombie_click.ACTIONS["play_shop_battle_drag_end"].x, zombie_click.ACTIONS["play_shop_battle_drag_end"].y), (252, 283))


class LegionShopTests(unittest.TestCase):
    def test_legion_shop_parser_is_registered(self) -> None:
        args = zombie_click.build_parser().parse_args(["legion-shop-purchases"])
        self.assertEqual(args.command, "legion-shop-purchases")

    def test_legion_shop_route_reuses_one_segmented_bottom_drag_and_completes_purchases(self) -> None:
        args = zombie_click.build_parser().parse_args(["legion-shop-purchases"])
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        events: list[object] = []
        with (
            patch.object(zombie_click, "prepare_command_bounds", return_value=bounds),
            patch.object(zombie_click, "perform_click", side_effect=lambda x, y, *_: (events.append((x, y)), "cgclick")[1]),
            patch.object(zombie_click, "perform_dismiss_click", side_effect=lambda x, y, *_: (events.append((x, y, "dismiss")), "cgclick")[1]),
            patch.object(zombie_click._legion, "_base_scroll_to_bottom", side_effect=lambda *_: events.append("drag")),
            patch.object(zombie_click, "sleep_between"),
        ):
            self.assertEqual(zombie_click.command_legion_shop_purchases(args), 0)

        self.assertEqual(events.count("drag"), 1)
        point = lambda name: zombie_click.scale_point(zombie_click.ACTIONS[name], bounds)
        self.assertEqual(
            events,
            [
                point("legion_shop"),
                "drag",
                point("legion_shop_gun_blueprint"),
                point("legion_shop_max"),
                point("legion_shop_buy"),
                (point("legion_shop_reward_dismiss")[0], point("legion_shop_reward_dismiss")[1], "dismiss"),
                point("legion_shop_modal_close"),
                point("legion_shop_base_powder"),
                point("legion_shop_max"),
                point("legion_shop_buy"),
                (point("legion_shop_reward_dismiss")[0], point("legion_shop_reward_dismiss")[1], "dismiss"),
                point("legion_shop_modal_close"),
                point("legion_shop_enhancer"),
                point("legion_shop_max"),
                point("legion_shop_buy"),
                (point("legion_shop_reward_dismiss")[0], point("legion_shop_reward_dismiss")[1], "dismiss"),
                point("legion_shop_modal_close"),
                point("legion_shop_close"),
            ],
        )

    def test_legion_shop_drag_coordinates_match_existing_canvas_drag(self) -> None:
        self.assertEqual(
            (zombie_click.ACTIONS["legion_shop_drag_start"].x, zombie_click.ACTIONS["legion_shop_drag_start"].y),
            (252, 760),
        )
        self.assertEqual(
            (zombie_click.ACTIONS["legion_shop_drag_end"].x, zombie_click.ACTIONS["legion_shop_drag_end"].y),
            (252, 120),
        )

    def test_legion_shop_purchase_coordinates_are_calibrated(self) -> None:
        self.assertEqual((zombie_click.ACTIONS["legion_shop_gun_blueprint"].x, zombie_click.ACTIONS["legion_shop_gun_blueprint"].y), (356, 436))
        self.assertEqual((zombie_click.ACTIONS["legion_shop_base_powder"].x, zombie_click.ACTIONS["legion_shop_base_powder"].y), (356, 581))
        self.assertEqual((zombie_click.ACTIONS["legion_shop_enhancer"].x, zombie_click.ACTIONS["legion_shop_enhancer"].y), (356, 726))


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

    def test_main_mock_legion_daily_rewards_dry_run_does_not_focus(self) -> None:
        with patch.object(zombie_click, "focus_game_window_at_start") as focus:
            self.assertEqual(
                zombie_click.main(
                    [
                        "--mock-bounds",
                        "2,33,508,949",
                        "legion-daily-rewards",
                        "--dry-run",
                    ]
                ),
                0,
            )

        focus.assert_not_called()

    def test_auto_backend_uses_cgclick(self) -> None:
        self.assertEqual(zombie_click.click_backend_candidates("auto"), ("cgclick",))

    def test_legion_daily_cut_modal_close_uses_the_verified_popup_close_point(self) -> None:
        self.assertEqual(zombie_click.ACTIONS["legion_modal_close"].x, 425)
        self.assertEqual(zombie_click.ACTIONS["legion_modal_close"].y, 228)

    def test_journey_resource_claim_opens_journey_then_claims_gold_and_wood_once(self) -> None:
        args = zombie_click.build_parser().parse_args(["journey-resource-claim"])
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        clicks: list[tuple[int, int]] = []
        with (
            patch.object(zombie_click, "prepare_command_bounds", return_value=bounds),
            patch.object(
                zombie_click,
                "perform_click",
                side_effect=lambda x, y, *_: (clicks.append((x, y)), "cgclick")[1],
            ),
            patch.object(zombie_click, "sleep_between"),
        ):
            self.assertEqual(zombie_click.command_journey_resource_claim(args), 0)

        point = lambda name: zombie_click.scale_point(zombie_click.ACTIONS[name], bounds)
        self.assertEqual(
            clicks,
            [
                point("journey_tab"),
                point("journey_gold_claim"),
                point("reward_dismiss"),
                point("journey_wood_claim"),
                point("reward_dismiss"),
            ],
        )

    def test_journey_resource_targets_remain_at_the_visible_bubble_centers(self) -> None:
        self.assertEqual(zombie_click.ACTIONS["journey_gold_claim"].x, 368)
        self.assertEqual(zombie_click.ACTIONS["journey_wood_claim"].x, 229)

    def test_cgclick_emits_a_complete_tap_sequence(self) -> None:
        self.assertIn("kCGEventMouseMoved", zombie_click.CGCLICK_SOURCE)
        self.assertIn("kCGMouseEventClickState", zombie_click.CGCLICK_SOURCE)
        self.assertIn("usleep(80000)", zombie_click.CGCLICK_SOURCE)

    def test_legion_sweep_confirmation_uses_the_verified_confirm_and_cancel_points(self) -> None:
        self.assertEqual((zombie_click.ACTIONS["legion_sweep_cancel"].x, zombie_click.ACTIONS["legion_sweep_cancel"].y), (187, 579))
        self.assertEqual((zombie_click.ACTIONS["legion_sweep_confirm"].x, zombie_click.ACTIONS["legion_sweep_confirm"].y), (321, 579))
        self.assertEqual((zombie_click.ACTIONS["legion_reward_popup_dismiss"].x, zombie_click.ACTIONS["legion_reward_popup_dismiss"].y), (250, 600))

    def test_quartz_emits_the_complete_tap_sequence(self) -> None:
        quartz = Mock(
            kCGEventSourceStateHIDSystemState="source-state",
            kCGEventMouseMoved="move",
            kCGEventLeftMouseDown="down",
            kCGEventLeftMouseUp="up",
            kCGMouseButtonLeft="left",
            kCGMouseEventClickState="click-state",
            kCGHIDEventTap="hid-tap",
        )
        quartz.CGEventCreateMouseEvent.side_effect = ["move-event", "down-event", "up-event"]
        with patch.dict(sys.modules, {"Quartz": quartz}), patch.object(zombie_click.time, "sleep") as sleep:
            self.assertTrue(zombie_click.click_quartz(10, 20))

        self.assertEqual(quartz.CGEventPost.call_args_list[0].args, ("hid-tap", "move-event"))
        self.assertEqual(quartz.CGEventPost.call_args_list[1].args, ("hid-tap", "down-event"))
        self.assertEqual(quartz.CGEventPost.call_args_list[2].args, ("hid-tap", "up-event"))
        self.assertEqual(sleep.call_args.args, (zombie_click.CLICK_HOLD_SECONDS,))

    def test_cliclick_emits_the_complete_tap_sequence(self) -> None:
        with (
            patch.object(zombie_click.shutil, "which", return_value="/usr/local/bin/cliclick"),
            patch.object(zombie_click.subprocess, "run") as run,
        ):
            self.assertTrue(zombie_click.click_cliclick(10, 20))

        self.assertEqual(
            run.call_args.args[0],
            ["/usr/local/bin/cliclick", "m:10,20", "dd:10,20", "w:80", "du:10,20"],
        )

    def test_system_events_backend_uses_the_complete_cgclick_tap(self) -> None:
        with patch.object(zombie_click, "click_cgclick_bin", return_value=True) as click:
            self.assertTrue(zombie_click.click_system_events(10, 20))

        click.assert_called_once_with(10, 20)

    def test_window_focus_osascript_times_out_instead_of_hanging(self) -> None:
        with patch.object(
            zombie_click.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["osascript"], 8.0),
        ):
            with self.assertRaisesRegex(zombie_click.ClickError, "window-focus osascript timed out"):
                zombie_click.run_osascript('tell application "System Events" to return "ok"')

    def test_auto_does_not_try_system_events_after_cgclick_failure(self) -> None:
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        with (
            patch.object(zombie_click, "focus_game_window"),
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
            ["cgclick", "cgclick"],
        )

    def test_perform_click_retries_one_delivery_failure_after_revalidating(self) -> None:
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        with (
            patch.object(zombie_click, "focus_game_window") as focus,
            patch.object(zombie_click, "ensure_unchanged_game_window") as verify,
            patch.object(
                zombie_click,
                "try_click_backend",
                side_effect=[(False, "unavailable"), (True, "")],
            ) as dispatch,
            patch.object(zombie_click, "wait_after_click"),
        ):
            self.assertEqual(zombie_click.perform_click(10, 20, "cgclick", bounds), "cgclick")

        self.assertEqual(dispatch.call_count, 2)
        self.assertEqual(focus.call_count, 2)
        self.assertEqual(verify.call_count, 2)

    def test_retry_refocuses_and_revalidates_before_its_second_dispatch(self) -> None:
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        events: list[str] = []
        with (
            patch.object(
                zombie_click,
                "focus_game_window",
                side_effect=lambda _: events.append("focus"),
            ),
            patch.object(
                zombie_click,
                "ensure_unchanged_game_window",
                side_effect=lambda _: events.append("verify"),
            ),
            patch.object(
                zombie_click,
                "try_click_backend",
                side_effect=[(False, "unavailable"), (True, "")],
            ),
            patch.object(zombie_click, "wait_after_click"),
        ):
            zombie_click.perform_click(10, 20, "cgclick", bounds)

        self.assertEqual(events, ["focus", "verify", "focus", "verify"])

    def test_perform_click_does_not_repeat_a_successful_dispatch(self) -> None:
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        with (
            patch.object(zombie_click, "focus_game_window"),
            patch.object(zombie_click, "ensure_unchanged_game_window"),
            patch.object(zombie_click, "try_click_backend", return_value=(True, "")) as dispatch,
            patch.object(zombie_click, "wait_after_click"),
        ):
            zombie_click.perform_click(10, 20, "cgclick", bounds)

        dispatch.assert_called_once_with("cgclick", 10, 20)

    def test_perform_dismiss_click_waits_half_second_after_dismissal(self) -> None:
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        with (
            patch.object(zombie_click, "perform_click", return_value="cgclick") as click,
            patch.object(zombie_click.time, "sleep") as sleep,
        ):
            self.assertEqual(zombie_click.perform_dismiss_click(10, 20, "cgclick", bounds), "cgclick")

        click.assert_called_once_with(10, 20, "cgclick", bounds, False)
        sleep.assert_called_once_with(0.5)

    def test_waits_reduce_configured_intervals_and_click_pacing(self) -> None:
        with patch.object(zombie_click.time, "sleep") as sleep:
            zombie_click.sleep_between(3.0)
            zombie_click.sleep_between(1.0)
            zombie_click.wait_after_click()

        self.assertEqual(sleep.call_args_list[0].args, (2.5,))
        self.assertEqual(sleep.call_args_list[1].args, (0.5,))
        post_click_wait = sleep.call_args_list[2].args[0]
        self.assertGreaterEqual(post_click_wait, 0.3)
        self.assertLessEqual(post_click_wait, 0.5)

    def test_business_wait_defaults_are_capped_except_ad_wait(self) -> None:
        parser = zombie_click.build_parser()
        expected = {
            "patrol-ads-batch": {"ad_wait": 33.0, "reward_wait": 0.5},
            "patrol-full-from-home": {
                "panel_wait": 0.5, "claim_wait": 0.5, "quick_reward_wait": 0.5,
                "quick_between": 0.5, "ad_wait": 33.0, "ad_close_wait": 0.5,
                "ad_between": 0.5, "close_wait": 0.5,
            },
            "patrol-ads-from-home": {"ad_wait": 33.0, "reward_wait": 0.5},
            "patrol-quick-batch": {"reward_wait": 0.5},
            "mail-claim": {"reward_wait": 0.5},
            "calendar-claim": {"reward_wait": 0.5},
            "welfare-claim": {"reward_wait": 0.5},
            "legion-daily-rewards": {"sweep_reward_wait": 0.5, "reward_page_wait": 0.5},
            "legion-reward-claims": {"sweep_reward_wait": 0.5, "reward_page_wait": 0.5},
            "legion-sweep-batch": {"reward_wait": 0.5},
        }
        for command, values in expected.items():
            required_times = {"patrol-quick-batch", "legion-sweep-batch"}
            args = parser.parse_args([command] + (["--times", "1"] if command in required_times else []))
            for name, value in values.items():
                self.assertEqual(getattr(args, name), value, (command, name))

    def test_default_patrol_ad_wait_is_33_seconds(self) -> None:
        parser = zombie_click.build_parser()
        for command in ("patrol-ads-batch", "patrol-full-from-home", "patrol-ads-from-home"):
            args = parser.parse_args([command])
            self.assertEqual(args.ad_wait, 33.0)

    def test_reward_dismiss_clicks_once_and_waits_half_second(self) -> None:
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        points = {"reward_dismiss": (252, 853)}
        with (
            patch.object(zombie_click, "perform_click", return_value="cgclick") as click,
            patch.object(zombie_click.time, "sleep") as sleep,
        ):
            zombie_click.dismiss_reward_once(
                points,
                "cgclick",
                bounds,
                label="test reward",
            )

        click.assert_called_once_with(252, 853, "cgclick", bounds, False)
        sleep.assert_called_once_with(0.5)

    def test_each_real_click_refocuses_before_verifying_and_dispatching(self) -> None:
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        events: list[str] = []
        with (
            patch.object(
                zombie_click,
                "focus_game_window",
                side_effect=lambda _: events.append("focus"),
            ),
            patch.object(
                zombie_click,
                "ensure_unchanged_game_window",
                side_effect=lambda _: events.append("verify"),
            ),
            patch.object(
                zombie_click,
                "try_click_backend",
                side_effect=lambda *_: (events.append("click"), (True, ""))[1],
            ),
            patch.object(zombie_click, "wait_after_click"),
        ):
            zombie_click.perform_click(10, 20, "cgclick", bounds)

        self.assertEqual(events, ["focus", "verify", "click"])

    def test_legion_reward_claims_runs_the_full_foreign_challenge_route(self) -> None:
        args = zombie_click.build_parser().parse_args(["legion-reward-claims"])
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        clicks: list[tuple[int, int]] = []
        waits: list[float] = []
        with (
            patch.object(zombie_click, "prepare_command_bounds", return_value=bounds),
            patch.object(
                zombie_click,
                "perform_click",
                side_effect=lambda x, y, *_: (clicks.append((x, y)), "cgclick")[1],
            ),
            patch.object(zombie_click, "sleep_between", side_effect=waits.append),
        ):
            self.assertEqual(zombie_click.command_legion_reward_claims(args), 0)

        self.assertEqual(
            clicks,
            [
                zombie_click.scale_point(zombie_click.ACTIONS["legion_tab"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["legion_foreign_challenge"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["legion_sweep"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["legion_sweep_confirm"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["legion_reward_popup_dismiss"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["legion_sweep"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["legion_sweep_confirm"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["legion_reward_popup_dismiss"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["legion_reward_left"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["legion_reward_claim_top"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["reward_dismiss"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["legion_personal_reward_tab"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["legion_personal_reward_claim_top"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["reward_dismiss"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["legion_reward_panel_close"], bounds),
                zombie_click.scale_point(zombie_click.ACTIONS["legion_foreign_challenge_back"], bounds),
            ],
        )
        self.assertEqual(waits, [0.8, 0.5, 0.6, 0.8, 0.5, 0.5])

    def test_legion_reward_claims_rejects_row_selection_flags(self) -> None:
        with self.assertRaises(SystemExit):
            zombie_click.build_parser().parse_args(["legion-reward-claims", "--rows", "1"])

    def test_legion_daily_rewards_delegates_full_foreign_challenge_route_after_daily_cut(self) -> None:
        args = zombie_click.build_parser().parse_args(["legion-daily-rewards"])
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        clicks: list[tuple[int, int]] = []
        with (
            patch.object(zombie_click, "prepare_command_bounds", return_value=bounds),
            patch.object(
                zombie_click,
                "perform_click",
                side_effect=lambda x, y, *_: (clicks.append((x, y)), "cgclick")[1],
            ),
            patch.object(zombie_click, "sleep_between"),
            patch.object(zombie_click, "command_legion_reward_claims", return_value=0) as claims,
            patch.object(zombie_click._legion, "command_legion_shop_purchases", return_value=0) as shop,
        ):
            self.assertEqual(zombie_click.command_legion_daily_rewards(args), 0)

        point = lambda name: zombie_click.scale_point(zombie_click.ACTIONS[name], bounds)
        self.assertEqual(
            clicks,
            [
                point("legion_tab"),
                point("legion_daily_cut"),
                point("legion_cut_once"),
                point("reward_dismiss"),
                point("legion_modal_close"),
            ],
        )
        delegated = claims.call_args.args[0]
        self.assertIs(delegated.mock_bounds, bounds)
        self.assertEqual(delegated.sweep_times, args.sweep_times)
        self.assertEqual(delegated.confirm_wait, args.confirm_wait)
        self.assertEqual(delegated.sweep_reward_wait, args.sweep_reward_wait)
        self.assertEqual(delegated.sweep_between, args.sweep_between)
        self.assertEqual(delegated.reward_page_wait, args.reward_page_wait)
        self.assertEqual(delegated.reward_wait, args.reward_wait)
        shop.assert_called_once()
        self.assertIs(shop.call_args.args[0].mock_bounds, bounds)

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
        self.assertEqual(click.call_count, 7)

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
        self.assertEqual(clicks.count(reward_dismiss), 1)
        self.assertNotIn(ad_close_lower, clicks)

    def test_post_ad_readiness_polls_until_the_calibrated_game_returns(self) -> None:
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        with (
            patch.object(
                zombie_click,
                "front_window_snapshot",
                side_effect=[
                    self.game_snapshot("广告"),
                    self.game_snapshot("向僵尸开炮"),
                ],
            ),
            patch.object(zombie_click.time, "monotonic", side_effect=[0.0, 0.2]),
            patch.object(zombie_click.time, "sleep") as sleep,
        ):
            zombie_click.ensure_game_ready_after_ad(bounds, timeout=2.0, interval=0.2)

        sleep.assert_called_once_with(0.2)

    def test_post_ad_readiness_raises_typed_error_after_deadline(self) -> None:
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        with (
            patch.object(zombie_click, "front_window_snapshot", return_value=self.game_snapshot("广告")),
            patch.object(zombie_click.time, "monotonic", side_effect=[0.0, 2.1]),
            patch.object(zombie_click.time, "sleep"),
        ):
            with self.assertRaises(zombie_click.AdReturnError):
                zombie_click.ensure_game_ready_after_ad(bounds, timeout=2.0, interval=0.2)

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

    def test_each_click_focuses_only_the_calibrated_game_window(self) -> None:
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
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
            zombie_click.focus_game_window(bounds)

        self.assertIn("((item 1 of p) as integer) = 2", osascript.call_args.args[0])

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

    def test_daily_rewards_command_handler_is_available(self) -> None:
        self.assertTrue(hasattr(zombie_click, "command_daily_rewards"))

    def test_calendar_claim_clicks_entry_gift_dismiss_and_close(self) -> None:
        args = zombie_click.build_parser().parse_args(["calendar-claim"])
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        clicks: list[tuple[int, int]] = []
        with (
            patch.object(zombie_click, "prepare_command_bounds", return_value=bounds),
            patch.object(
                zombie_click,
                "perform_click",
                side_effect=lambda x, y, *_: (clicks.append((x, y)), "cgclick")[1],
            ),
            patch.object(zombie_click, "sleep_between"),
        ):
            self.assertEqual(zombie_click.command_calendar_claim(args), 0)

        point = lambda name: zombie_click.scale_point(zombie_click.ACTIONS[name], bounds)
        self.assertEqual(clicks, [point("calendar_top"), point("calendar_gift"), point("reward_dismiss"), point("calendar_close")])

    def test_welfare_claim_clicks_only_free_popup_dismiss_and_back(self) -> None:
        args = zombie_click.build_parser().parse_args(["welfare-claim"])
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        clicks: list[tuple[int, int]] = []
        with (
            patch.object(zombie_click, "prepare_command_bounds", return_value=bounds),
            patch.object(
                zombie_click,
                "perform_click",
                side_effect=lambda x, y, *_: (clicks.append((x, y)), "cgclick")[1],
            ),
            patch.object(zombie_click, "sleep_between"),
        ):
            self.assertEqual(zombie_click.command_welfare_claim(args), 0)

        point = lambda name: zombie_click.scale_point(zombie_click.ACTIONS[name], bounds)
        self.assertEqual(
            clicks,
            [point("welfare_cluster"), point("welfare_reward_popup_dismiss"), point("back_bottom_left")],
        )

    def test_daily_rewards_runs_all_eight_phases_in_order_with_shared_bounds(self) -> None:
        args = argparse.Namespace(
            mock_bounds=None,
            fit=True,
            dry_run=False,
            backend="cgclick",
        )
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        phases: list[tuple[str, zombie_click.Bounds]] = []
        with (
            patch.object(zombie_click, "front_window_snapshot", return_value=self.game_snapshot("向僵尸开炮")),
            patch.object(zombie_click, "fit_game_window", return_value=bounds),
            patch.object(
                zombie_click,
                "command_patrol_full_from_home",
                side_effect=lambda phase_args: phases.append(("patrol", phase_args.mock_bounds)),
            ),
            patch.object(
                zombie_click,
                "command_calendar_claim",
                side_effect=lambda phase_args: phases.append(("calendar", phase_args.mock_bounds)),
            ),
            patch.object(
                zombie_click,
                "command_welfare_claim",
                side_effect=lambda phase_args: phases.append(("welfare", phase_args.mock_bounds)),
            ),
            patch.object(
                zombie_click,
                "command_mail_claim",
                side_effect=lambda phase_args: phases.append(("mail", phase_args.mock_bounds)),
            ),
            patch.object(
                zombie_click,
                "command_legion_daily_rewards",
                side_effect=lambda phase_args: phases.append(("legion", phase_args.mock_bounds)),
            ),
            patch.object(
                zombie_click,
                "command_journey_resource_claim",
                side_effect=lambda phase_args: phases.append(("journey", phase_args.mock_bounds)),
            ),
            patch.object(
                zombie_click,
                "command_base_training_hall",
                side_effect=lambda phase_args: phases.append(("base", phase_args.mock_bounds)),
            ),
            patch.object(
                zombie_click,
                "command_shop_training_hall",
                side_effect=lambda phase_args: phases.append(("shop", phase_args.mock_bounds)),
            ),
        ):
            self.assertEqual(zombie_click.command_daily_rewards(args), 0)

        self.assertEqual(
            phases,
            [("patrol", bounds), ("calendar", bounds), ("welfare", bounds), ("mail", bounds), ("legion", bounds), ("journey", bounds), ("base", bounds), ("shop", bounds)],
        )

    def test_daily_rewards_from_step_three_skips_patrol_and_calendar(self) -> None:
        args = zombie_click.build_parser().parse_args(
            ["--mock-bounds", "2,33,508,949", "daily-rewards", "--from-step", "3", "--dry-run"]
        )
        phases: list[str] = []
        with (
            patch.object(zombie_click, "command_patrol_full_from_home") as patrol,
            patch.object(zombie_click, "command_calendar_claim") as calendar,
            patch.object(
                zombie_click,
                "command_welfare_claim",
                side_effect=lambda _: phases.append("welfare"),
            ),
            patch.object(
                zombie_click,
                "command_mail_claim",
                side_effect=lambda _: phases.append("mail"),
            ),
            patch.object(
                zombie_click,
                "command_legion_daily_rewards",
                side_effect=lambda _: phases.append("legion"),
            ),
            patch.object(
                zombie_click,
                "command_journey_resource_claim",
                side_effect=lambda _: phases.append("journey"),
            ),
            patch.object(
                zombie_click,
                "command_base_training_hall",
                side_effect=lambda _: phases.append("base"),
            ),
            patch.object(
                zombie_click,
                "command_shop_training_hall",
                side_effect=lambda _: phases.append("shop"),
            ),
            patch("builtins.print") as print_mock,
        ):
            self.assertEqual(zombie_click.command_daily_rewards(args), 0)

        patrol.assert_not_called()
        calendar.assert_not_called()
        self.assertEqual(phases, ["welfare", "mail", "legion", "journey", "base", "shop"])
        summary = "\n".join(str(call.args[0]) for call in print_mock.call_args_list)
        self.assertIn("patrol=skipped", summary)
        self.assertIn("calendar=skipped", summary)

    def test_daily_rewards_from_step_defaults_to_one(self) -> None:
        args = zombie_click.build_parser().parse_args(["daily-rewards"])
        self.assertEqual(args.from_step, 1)

    def test_daily_rewards_from_step_rejects_out_of_range_values(self) -> None:
        for value in ("0", "9"):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                zombie_click.build_parser().parse_args(["daily-rewards", "--from-step", value])

    def test_daily_rewards_continues_after_a_recovered_calendar_failure(self) -> None:
        args = argparse.Namespace(
            mock_bounds=zombie_click.Bounds("MOCK", "mock", 2, 33, 508, 949),
            dry_run=True,
            backend="cgclick",
        )
        with (
            patch.object(zombie_click, "command_patrol_full_from_home", return_value=0),
            patch.object(
                zombie_click,
                "command_calendar_claim",
                side_effect=zombie_click.ClickDeliveryError("calendar delivery failed"),
            ),
            patch.object(zombie_click, "recover_phase", return_value=None, create=True) as recover,
            patch.object(zombie_click, "command_welfare_claim", return_value=0) as welfare,
            patch.object(zombie_click, "command_mail_claim", return_value=0),
            patch.object(zombie_click, "command_legion_daily_rewards", return_value=0),
        ):
            self.assertEqual(zombie_click.command_daily_rewards(args), 0)

        recover.assert_called_once()
        welfare.assert_called_once()

    def test_daily_rewards_stops_after_window_state_failure(self) -> None:
        args = argparse.Namespace(
            mock_bounds=zombie_click.Bounds("MOCK", "mock", 2, 33, 508, 949),
            dry_run=True,
            backend="cgclick",
        )
        with (
            patch.object(
                zombie_click,
                "command_patrol_full_from_home",
                side_effect=zombie_click.WindowStateError("wrong app"),
            ),
            patch.object(zombie_click, "command_calendar_claim") as calendar,
        ):
            with self.assertRaisesRegex(zombie_click.WindowStateError, "wrong app"):
                zombie_click.command_daily_rewards(args)

        calendar.assert_not_called()

    def test_daily_rewards_reports_completed_and_skipped_phases_before_reraising_fatal_error(self) -> None:
        args = argparse.Namespace(
            mock_bounds=zombie_click.Bounds("MOCK", "mock", 2, 33, 508, 949),
            dry_run=True,
            backend="cgclick",
        )
        with (
            patch.object(zombie_click, "command_patrol_full_from_home", return_value=0),
            patch.object(
                zombie_click,
                "command_calendar_claim",
                side_effect=zombie_click.WindowStateError("wrong app"),
            ),
            patch.object(zombie_click, "command_welfare_claim"),
            patch.object(zombie_click, "command_mail_claim"),
            patch.object(zombie_click, "command_legion_daily_rewards"),
            patch("builtins.print") as print_mock,
        ):
            with self.assertRaisesRegex(zombie_click.WindowStateError, "wrong app"):
                zombie_click.command_daily_rewards(args)

        printed = "\n".join(str(call.args[0]) for call in print_mock.call_args_list)
        self.assertIn("patrol=completed", printed)
        self.assertIn("calendar=fatal_failure", printed)
        self.assertIn("welfare=skipped", printed)

    def test_daily_rewards_prints_partial_when_a_phase_recovers(self) -> None:
        args = argparse.Namespace(
            mock_bounds=zombie_click.Bounds("MOCK", "mock", 2, 33, 508, 949),
            dry_run=True,
            backend="cgclick",
        )
        with (
            patch.object(
                zombie_click,
                "command_patrol_full_from_home",
                side_effect=zombie_click.ClickDeliveryError("delivery failed"),
            ),
            patch.object(zombie_click, "recover_phase", return_value=None),
            patch.object(zombie_click, "command_calendar_claim", return_value=0),
            patch.object(zombie_click, "command_welfare_claim", return_value=0),
            patch.object(zombie_click, "command_mail_claim", return_value=0),
            patch.object(zombie_click, "command_legion_daily_rewards", return_value=0),
            patch("builtins.print") as print_mock,
        ):
            self.assertEqual(zombie_click.command_daily_rewards(args), 0)

        self.assertTrue(any("daily rewards partial" in str(call.args[0]) for call in print_mock.call_args_list))
