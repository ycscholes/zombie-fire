import argparse
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

    def test_legion_sweep_confirmation_uses_the_verified_confirm_and_cancel_points(self) -> None:
        self.assertEqual((zombie_click.ACTIONS["legion_sweep_cancel"].x, zombie_click.ACTIONS["legion_sweep_cancel"].y), (187, 579))
        self.assertEqual((zombie_click.ACTIONS["legion_sweep_confirm"].x, zombie_click.ACTIONS["legion_sweep_confirm"].y), (321, 579))
        self.assertEqual((zombie_click.ACTIONS["legion_reward_popup_dismiss"].x, zombie_click.ACTIONS["legion_reward_popup_dismiss"].y), (250, 600))

    def test_system_events_click_uses_named_finite_timeout(self) -> None:
        with patch.object(zombie_click.subprocess, "run") as run:
            run.return_value = Mock(returncode=0, stdout="", stderr="")

            self.assertTrue(zombie_click.click_system_events(10, 20))

        self.assertEqual(zombie_click.SYSTEM_EVENTS_CLICK_TIMEOUT_SECONDS, 8.0)
        self.assertEqual(run.call_args.kwargs["timeout"], zombie_click.SYSTEM_EVENTS_CLICK_TIMEOUT_SECONDS)

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

    def test_waits_are_reduced_by_one_second_with_a_half_second_floor(self) -> None:
        with patch.object(zombie_click.time, "sleep") as sleep:
            zombie_click.sleep_between(3.0)
            zombie_click.sleep_between(1.0)
            zombie_click.wait_after_click()

        self.assertEqual(sleep.call_args_list[0].args, (2.0,))
        self.assertEqual(sleep.call_args_list[1].args, (0.5,))
        post_click_wait = sleep.call_args_list[2].args[0]
        self.assertGreaterEqual(post_click_wait, 1.5)
        self.assertLessEqual(post_click_wait, 2.5)

    def test_repeated_reward_dismiss_waits_exactly_one_second_before_the_second_tap(self) -> None:
        bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)
        points = {"reward_dismiss": (252, 853)}
        with (
            patch.object(zombie_click, "perform_click", return_value="cgclick") as click,
            patch.object(zombie_click.time, "sleep") as sleep,
        ):
            zombie_click.dismiss_reward_twice(
                points,
                "cgclick",
                bounds,
                wait=1.0,
                label="test reward",
            )

        self.assertEqual(click.call_args_list[0].args, (252, 853, "cgclick", bounds, False))
        self.assertEqual(click.call_args_list[1].args, (252, 853, "cgclick", bounds))
        sleep.assert_called_once_with(1.0)

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
        self.assertEqual(waits, [0.8, 1.2, 0.6, 0.8, 1.2, 4.0])

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

    def test_daily_rewards_runs_the_five_phases_in_order_with_shared_bounds(self) -> None:
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
        ):
            self.assertEqual(zombie_click.command_daily_rewards(args), 0)

        self.assertEqual(
            phases,
            [("patrol", bounds), ("calendar", bounds), ("welfare", bounds), ("mail", bounds), ("legion", bounds)],
        )

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
