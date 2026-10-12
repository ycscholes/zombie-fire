"""组合任务复用、续跑参数和失败传播的离线验证。"""
import io
import unittest
from contextlib import ExitStack, redirect_stdout
from unittest.mock import patch

from scripts import zombie_click
from scripts.zombie_tasks import legion, patrol


class TaskCompositionTests(unittest.TestCase):
    def setUp(self):
        self.bounds = zombie_click.Bounds("WeChat", "com.tencent.xinWeChat", 2, 33, 508, 949)

    def test_legion_composes_same_suffix_for_live_and_dry_run(self):
        tasks = ("daily_cut", "foreign_rewards", "shop", "journey_gifts")
        names = ("_run_legion_daily_cut", "command_legion_reward_claims",
                 "command_legion_shop_purchases", "command_legion_journey_gifts")
        for dry_run in (False, True):
            for start in (None, *tasks):
                with self.subTest(dry_run=dry_run, start=start):
                    args = zombie_click.build_parser().parse_args(["legion-daily-rewards"])
                    args.dry_run, args.from_task = dry_run, start
                    calls = []
                    with patch.object(legion, "prepare_command_bounds", return_value=self.bounds), redirect_stdout(io.StringIO()):
                        with ExitStack() as stack:
                            for task, name in zip(tasks, names):
                                stack.enter_context(patch.object(legion, name, side_effect=lambda child, task=task: calls.append((task, child))))
                            legion.command_legion_daily_rewards(args)
                    expected = tasks[tasks.index(start):] if start else tasks
                    self.assertEqual([task for task, _ in calls], list(expected))
                    for _, child in calls:
                        self.assertIsNone(child.from_task)
                        self.assertEqual(child.mock_bounds, self.bounds)
                        self.assertFalse(child.fit)
                        self.assertEqual(child.dry_run, dry_run)
                    self.assertEqual(args.from_task, start)

    def test_legion_claims_reuses_sweep_batch_and_skips_it_when_resuming_rewards(self):
        for start in (None, "legion_rewards", "personal_rewards"):
            args = zombie_click.build_parser().parse_args(["legion-reward-claims"])
            args.from_task = start
            with patch.object(legion, "prepare_command_bounds", return_value=self.bounds), patch.object(legion, "perform_tab_click"), patch.object(legion, "perform_action"), patch.object(legion, "perform_click"), patch.object(legion, "perform_reward_click"), patch.object(legion, "perform_dismiss_click"), patch.object(legion, "sleep_between"), patch.object(legion, "command_legion_sweep_batch", return_value=0) as batch, redirect_stdout(io.StringIO()):
                legion.command_legion_reward_claims(args)
            if start is None:
                batch.assert_called_once()
                child = batch.call_args.args[0]
                self.assertEqual(child.times, args.sweep_times)
                self.assertEqual(child.mock_bounds, self.bounds)
                self.assertIsNone(child.from_task)
            else:
                batch.assert_not_called()

    def test_home_ads_reuses_batch_and_does_not_close_after_failure(self):
        args = zombie_click.build_parser().parse_args(["patrol-ads-from-home", "--times", "2"])
        for failed in (False, True):
            events = []
            def batch(child):
                self.assertEqual(child.times, 2)
                self.assertEqual(child.mock_bounds, self.bounds)
                self.assertFalse(child.fit)
                events.append("batch")
                if failed:
                    raise zombie_click.ClickDeliveryError("delivery failed")
                return 0
            with patch.object(patrol, "prepare_command_bounds", return_value=self.bounds), patch.object(patrol, "_perform_event", side_effect=lambda event, *_: events.append(event)), patch.object(patrol, "command_patrol_ads_batch", side_effect=batch), redirect_stdout(io.StringIO()):
                if failed:
                    with self.assertRaises(zombie_click.ClickDeliveryError):
                        patrol.command_patrol_ads_from_home(args)
                else:
                    patrol.command_patrol_ads_from_home(args)
            self.assertEqual(events, ["patrol_truck", "batch"] + ([] if failed else ["patrol_close"]))


if __name__ == "__main__":
    unittest.main()
