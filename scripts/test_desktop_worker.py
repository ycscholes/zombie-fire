"""桌面执行器的协议、每日任务计划与失败停止行为测试。"""

from __future__ import annotations

import json
import argparse
import io
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from scripts import desktop_worker
from scripts.zombie_tasks import base as base_tasks
from scripts.zombie_tasks import legion as legion_tasks


class DesktopWorkerTests(unittest.TestCase):
    def test_catalog_exposes_the_daily_task_ids_and_typed_command_arguments(self) -> None:
        catalog = desktop_worker.build_catalog()

        self.assertEqual(len(catalog["daily_tasks"]), 26)
        self.assertEqual(catalog["daily_tasks"][0]["id"], "patrol.claim")
        self.assertEqual(catalog["daily_tasks"][3]["id"], "mechanical.shock")
        self.assertEqual(catalog["daily_tasks"][4]["id"], "pass.daily")
        self.assertEqual(catalog["daily_tasks"][5]["id"], "armed.descent")
        self.assertEqual(catalog["daily_tasks"][6]["id"], "mimic.card_library")
        pass_command = next(item for item in catalog["commands"] if item["id"] == "battle-pass-daily")
        self.assertEqual(
            {arg["name"]: tuple(arg["choices"] or ()) for arg in pass_command["args"]},
            {"free_claim_state": ("available", "claimed"), "work_plan_sign_state": ("available", "claimed"), "backend": ("auto", "cgclick", "quartz", "cliclick", "system-events")},
        )
        command = next(item for item in catalog["commands"] if item["id"] == "patrol-full-from-home")
        fit = next(item for item in command["args"] if item["name"] == "fit")
        self.assertEqual(fit["type"], "boolean")
        self.assertEqual(fit["flag"], "--fit")
        self.assertEqual(fit["negative_flag"], "--no-fit")
        self.assertIsNone(fit["position"])
        self.assertFalse(fit["required"])
        ad_wait = next(item for item in command["args"] if item["name"] == "ad_wait")
        self.assertEqual(ad_wait["type"], "number")
        self.assertEqual(
            next(item for item in catalog["commands"] if item["id"] == "patrol-full-from-home")["entry_pages"]["quick_patrol"],
            "巡逻面板",
        )
        self.assertEqual(
            next(item for item in catalog["commands"] if item["id"] == "base-training-hall")["entry_pages"]["deep_abyss"],
            "训练大厅列表",
        )
        self.assertEqual(
            next(item for item in catalog["commands"] if item["id"] == "daily-rewards")["entry_pages"]["patrol.quick_patrol"],
            "巡逻面板",
        )

    def test_catalog_has_daily_routes_and_shared_safe_defaults_without_changing_counts_or_waits(self) -> None:
        catalog = desktop_worker.build_catalog()
        tasks = {task["id"]: task for task in catalog["daily_tasks"]}
        self.assertEqual(tuple(task["id"] for task in catalog["daily_tasks"]), desktop_worker.DAILY_TASK_IDS)
        self.assertEqual((tasks["patrol.claim"]["tab"], tasks["patrol.claim"]["module"]), ("首页", "巡逻"))
        self.assertEqual((tasks["base.global_rescue"]["tab"], tasks["base.global_rescue"]["module"]), ("基地", "历练大厅"))
        commands = {command["id"]: {arg["name"]: arg for arg in command["args"]} for command in catalog["commands"]}
        shared_fields: dict[str, list[dict[str, object]]] = {}
        for command in catalog["commands"]:
            for argument in command["args"]:
                if argument.get("shared_key"):
                    shared_fields.setdefault(argument["shared_key"], []).append(argument)
                choices = set(argument.get("choices") or ())
                if {"available", "claimed"} <= choices:
                    self.assertEqual(argument["default"], "available")
                if {"checked", "unchecked"} <= choices:
                    self.assertEqual(argument["default"], "checked")
                if argument["name"].endswith("task_claims"):
                    self.assertEqual(argument["default"], 3)
        for fields in shared_fields.values():
            for key in ("default", "choices", "required"):
                self.assertTrue(all(field.get(key) == fields[0].get(key) for field in fields))
        self.assertEqual(commands["armed-descent"]["free_draw_state"]["default"], "available")
        self.assertEqual(commands["armed-descent"]["skip_animation_state"]["default"], "checked")
        self.assertEqual(commands["mimic-card-library"]["mimic_task_claims"]["default"], 3)
        self.assertEqual(commands["patrol-full-from-home"]["quick_times"]["default"], 3)
        self.assertEqual(commands["patrol-full-from-home"]["claim_wait"]["default"], 0.3)
        self.assertEqual(commands["patrol-quick-batch"]["times"]["default"], 3)
        self.assertFalse(commands["patrol-quick-batch"]["times"]["required"])
        self.assertEqual(commands["patrol-ads-batch"]["reward_wait"]["default"], commands["patrol-full-from-home"]["ad_reward_wait"]["default"])
        self.assertEqual(commands["legion-sweep-batch"]["times"]["default"], commands["legion-daily-rewards"]["sweep_times"]["default"])
        command_order = [command["id"] for command in catalog["commands"]]
        self.assertLess(command_order.index("patrol-full-from-home"), command_order.index("mechanical-shock"))
        self.assertLess(command_order.index("base-training-hall-global-rescue"), command_order.index("base-training-hall-global-expedition"))
        self.assertLess(command_order.index("base-training-hall-global-expedition"), command_order.index("base-training-hall-deep-abyss"))

    def test_daily_run_uses_saved_single_command_values_in_the_actual_handler(self) -> None:
        events: list[dict[str, object]] = []
        status = desktop_worker.run_request(
            {
                "mode": "daily",
                "task_ids": ["mechanical.shock"],
                "phase_args": {
                    "mechanical_shock": [
                        "--mechanical-shock-skip-animation-state", "checked",
                        "--mechanical-shock-task-claims", "0",
                        "--mechanical-shock-mech-fight-claim-state", "claimed",
                        "--backend", "quartz",
                    ],
                },
                "dry_run": True,
            },
            events.append,
        )

        self.assertEqual(status, "dry_run_completed")
        self.assertTrue(any("task_claims=0" in event.get("message", "") and "mech_fight_claim=claimed" in event.get("message", "") for event in events if event["type"] == "log"))

    def test_full_daily_command_uses_the_same_phase_arguments_as_daily_mode(self) -> None:
        events: list[dict[str, object]] = []
        status = desktop_worker.run_request(
            {
                "mode": "command",
                "command": "daily-rewards",
                "task_ids": [],
                "args": [
                    "--from-task=mechanical.shock", "--mechanical-shock-task-claims", "0",
                    "--mechanical-shock-skip-animation-state", "checked", "--mechanical-shock-mech-fight-claim-state", "claimed",
                    "--pass-free-claim-state", "available", "--pass-work-plan-sign-state", "available",
                    "--armed-skip-animation-state", "checked", "--armed-free-draw-state", "available", "--armed-task-claims", "0",
                    "--mimic-skip-animation-state", "checked", "--mimic-free-draw-state", "available", "--mimic-task-claims", "0", "--mimic-one-click-claim-state", "available",
                ],
                "dry_run": True,
            },
            events.append,
        )

        self.assertEqual(status, "dry_run_completed")
        started = [event["task_id"] for event in events if event["type"] == "task_started"]
        self.assertEqual(started[0], "mechanical.shock")
        plan = next(event for event in events if event["type"] == "run_plan")
        self.assertEqual(plan["task_count"], len(desktop_worker.DAILY_TASK_IDS) - desktop_worker.DAILY_TASK_IDS.index("mechanical.shock"))
        self.assertEqual(plan["task_ids"], started)
        self.assertTrue(any("task_claims=0" in event.get("message", "") and "mech_fight_claim=claimed" in event.get("message", "") for event in events if event["type"] == "log"))

    def test_daily_plan_keeps_enabled_order_and_resumes_at_enabled_task(self) -> None:
        plan = desktop_worker.build_daily_plan(
            ["shop.special_pack_gold", "patrol.ad_patrol", "calendar", "patrol.claim"],
            from_task="calendar",
        )

        self.assertEqual(
            [(phase.id, phase.task_ids) for phase in plan],
            [
                ("calendar", ("calendar",)),
                ("shop", ("shop.special_pack_gold",)),
            ],
        )

    def test_daily_plan_rejects_unknown_duplicate_and_disabled_start_ids(self) -> None:
        for task_ids, from_task in (
            (["does.not.exist"], None),
            (["calendar", "calendar"], None),
            (["calendar"], "welfare"),
        ):
            with self.subTest(task_ids=task_ids, from_task=from_task):
                with self.assertRaises(desktop_worker.WorkerError):
                    desktop_worker.build_daily_plan(task_ids, from_task=from_task)

    def test_command_arguments_are_parsed_without_shell_interpretation(self) -> None:
        args = desktop_worker.parse_command_args(
            "patrol-full-from-home", ["--quick-times", "2", "--no-fit"], dry_run=True
        )

        self.assertEqual(args.quick_times, 2)
        self.assertFalse(args.fit)
        with self.assertRaises(desktop_worker.WorkerError):
            desktop_worker.parse_command_args("unknown-command", [], dry_run=False)
        with self.assertRaises(desktop_worker.WorkerError):
            desktop_worker.parse_command_args("patrol-full-from-home", ["--help"], dry_run=False)
        with self.assertRaises(desktop_worker.WorkerError):
            desktop_worker.parse_command_args(
                "patrol-full-from-home", ["--quick-times", "2; rm -rf /"], dry_run=False
            )

    def test_packaged_cgclick_helper_uses_the_embedded_resource_without_compilation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / "resources" / "bin" / "zombie_cgclick"
            helper.parent.mkdir(parents=True)
            helper.write_text("packaged helper", encoding="utf-8")
            helper.chmod(0o755)
            with (
                mock.patch.dict(os.environ, {}, clear=False),
                mock.patch.object(desktop_worker.common.sys, "frozen", True, create=True),
                mock.patch.object(desktop_worker.common.sys, "_MEIPASS", directory, create=True),
                mock.patch.object(desktop_worker.common.subprocess, "run") as run_process,
            ):
                os.environ.pop("ZOMBIE_CGCLICK_BIN", None)
                self.assertTrue(desktop_worker.common.ensure_cgclick())
                self.assertEqual(desktop_worker.common.CGCLICK_BIN, str(helper))
                run_process.assert_not_called()

    def test_cancellation_is_checked_before_the_next_input(self) -> None:
        token = desktop_worker.CancellationToken()
        previous = desktop_worker._install_cancellation(token)
        try:
            token.request_stop()
            with self.assertRaises(desktop_worker.WorkerCancelled):
                desktop_worker.common.input_preflight(
                    desktop_worker.common.Bounds("WeChat", "com.tencent.xinWeChat", 0, 0, 508, 949)
                )
        finally:
            desktop_worker._restore_cancellation(previous)

    def test_control_reader_accepts_jsonl_stop_after_the_run_request(self) -> None:
        token = desktop_worker.CancellationToken()
        control_lines = io.StringIO('{"type":"other"}\n{"type":"stop"}\n')
        with mock.patch.object(desktop_worker.sys, "stdin", control_lines):
            reader = threading.Thread(target=desktop_worker._read_control_messages, args=(token,))
            reader.start()
            reader.join(timeout=1.0)

        self.assertFalse(reader.is_alive())
        self.assertTrue(token.stopped)

    def test_control_reader_stops_live_run_on_parent_eof_but_allows_dry_run_eof(self) -> None:
        live_token = desktop_worker.CancellationToken()
        previous = desktop_worker._install_cancellation(live_token)
        with mock.patch.object(desktop_worker.sys, "stdin", io.StringIO("")):
            desktop_worker._read_control_messages(live_token, stop_on_disconnect=True)
        try:
            with self.assertRaises(desktop_worker.WorkerCancelled):
                desktop_worker.common.input_preflight(
                    desktop_worker.common.Bounds("WeChat", "com.tencent.xinWeChat", 0, 0, 508, 949)
                )
        finally:
            desktop_worker._restore_cancellation(previous)

        dry_run_token = desktop_worker.CancellationToken()
        with mock.patch.object(desktop_worker.sys, "stdin", io.StringIO("")):
            desktop_worker._read_control_messages(dry_run_token, stop_on_disconnect=False)
        dry_run_token.check()

    def test_daily_execution_stops_at_first_failed_task(self) -> None:
        plan = desktop_worker.build_daily_plan(
            ["calendar", "welfare", "mail", "legion.daily_cut"]
        )
        events: list[dict[str, object]] = []
        invoked: list[str] = []

        def emit(event: dict[str, object]) -> None:
            events.append(event)

        def run_phase(phase: desktop_worker.DailyPhase, task_event) -> None:
            invoked.append(phase.id)
            first = phase.task_ids[0]
            task_event(first, "started")
            if first == "welfare":
                raise RuntimeError("simulated task failure")
            task_event(first, "completed")

        status = desktop_worker.execute_daily_plan(plan, run_phase, emit)

        self.assertEqual(status, "failed")
        self.assertEqual(invoked, ["calendar", "welfare"])
        self.assertEqual(
            [(event["type"], event.get("task_id"), event.get("status")) for event in events],
            [
                ("task_started", "calendar", None),
                ("task_finished", "calendar", "completed"),
                ("task_started", "welfare", None),
                ("task_finished", "welfare", "failed"),
                ("error", None, None),
                ("run_finished", None, "failed"),
            ],
        )

    def test_terminal_task_callback_status_aborts_remaining_tasks_immediately(self) -> None:
        plan = desktop_worker.build_daily_plan(["calendar", "mail"])
        events: list[dict[str, object]] = []
        invoked: list[str] = []

        def run_phase(phase: desktop_worker.DailyPhase, task_event) -> None:
            invoked.append(phase.id)
            task_id = phase.task_ids[0]
            task_event(task_id, "started")
            task_event(task_id, "failed")
            invoked.append("must-not-run")

        status = desktop_worker.execute_daily_plan(plan, run_phase, events.append)

        self.assertEqual(status, "failed")
        self.assertEqual(invoked, ["calendar"])
        self.assertEqual(events[-1], {"type": "run_finished", "status": "failed"})

    def test_live_preflight_and_session_teardown_output_are_jsonl_events(self) -> None:
        bounds = desktop_worker.common.Bounds("WeChat", "com.tencent.xinWeChat", 0, 0, 508, 949)
        events: list[dict[str, object]] = []

        def fake_preflight(*, fit: bool, token: desktop_worker.CancellationToken) -> object:
            desktop_worker.common.start_input_session()
            desktop_worker.common.bind_input_session(bounds)
            return bounds

        def fake_phase(phase, report_task, **kwargs) -> None:
            for task_id in phase.task_ids:
                report_task(task_id, "started")
                report_task(task_id, "completed")

        with (
            mock.patch.object(desktop_worker, "_preflight_live", side_effect=fake_preflight),
            mock.patch.object(desktop_worker, "_call_phase_with_events", side_effect=fake_phase),
        ):
            status = desktop_worker.run_request(
                {"mode": "daily", "task_ids": ["calendar"], "dry_run": False},
                events.append,
            )

        self.assertEqual(status, "completed")
        log_messages = [event.get("message", "") for event in events if event["type"] == "log"]
        self.assertTrue(any("input-session: start" in message for message in log_messages))
        self.assertTrue(any("input-session: bind" in message for message in log_messages))
        self.assertTrue(any("input-session: end" in message for message in log_messages))
        self.assertEqual(events[-1], {"type": "run_finished", "status": "completed"})

    def test_single_command_preflight_and_teardown_output_are_jsonl_events(self) -> None:
        bounds = desktop_worker.common.Bounds("WeChat", "com.tencent.xinWeChat", 0, 0, 508, 949)
        events: list[dict[str, object]] = []
        original_builder = desktop_worker.cli.build_parser

        def fake_builder():
            parser = original_builder()
            subparsers = next(
                action for action in parser._actions
                if isinstance(action, argparse._SubParsersAction)
            )
            subparsers.choices["patrol-full-from-home"].set_defaults(func=lambda _args: 0)
            return parser

        def fake_preflight(*, fit: bool, token: desktop_worker.CancellationToken) -> object:
            desktop_worker.common.start_input_session()
            desktop_worker.common.bind_input_session(bounds)
            return bounds

        with (
            mock.patch.object(desktop_worker.cli, "build_parser", side_effect=fake_builder),
            mock.patch.object(desktop_worker, "_preflight_live", side_effect=fake_preflight),
        ):
            status = desktop_worker.run_request(
                {"mode": "command", "command": "patrol-full-from-home", "dry_run": False},
                events.append,
            )

        self.assertEqual(status, "completed")
        self.assertEqual(events[0], {"type": "task_started", "task_id": "patrol-full-from-home"})
        messages = [event.get("message", "") for event in events if event["type"] == "log"]
        self.assertTrue(any("input-session: start" in message for message in messages))
        self.assertTrue(any("input-session: bind" in message for message in messages))
        self.assertTrue(any("input-session: end" in message for message in messages))
        self.assertEqual(events[-1], {"type": "run_finished", "status": "completed"})

    def test_stop_during_live_preflight_emits_stopped_without_running_a_task(self) -> None:
        events: list[dict[str, object]] = []

        def stop_during_preflight(*, fit: bool, token: desktop_worker.CancellationToken) -> object:
            token.request_stop()
            token.check()

        with (
            mock.patch.object(desktop_worker, "_preflight_live", side_effect=stop_during_preflight),
            mock.patch.object(desktop_worker, "_call_phase_with_events") as run_phase,
        ):
            status = desktop_worker.run_request(
                {"mode": "daily", "task_ids": ["calendar"], "dry_run": False},
                events.append,
            )

        self.assertEqual(status, "stopped")
        run_phase.assert_not_called()
        self.assertFalse(any(event["type"] == "task_started" for event in events))
        self.assertEqual(events[-1], {"type": "run_finished", "status": "stopped"})

    def test_base_bottom_cards_scroll_when_terminal_crisis_was_removed(self) -> None:
        bounds = desktop_worker.common.Bounds("mock", "mock", 2, 33, 508, 949)

        for bottom_task in ("battlefield_contest", "element_trial"):
            with self.subTest(bottom_task=bottom_task):
                trace: list[str] = []
                args = argparse.Namespace(
                    from_task=None,
                    battle_times=5,
                    dry_run=False,
                    skip_scroll=False,
                    desktop_navigate_base=True,
                    desktop_navigate_training_hall=True,
                    desktop_task_ids=["global_rescue", bottom_task],
                    desktop_task_event=lambda task, status: trace.append(f"{task}:{status}"),
                    backend="cgclick",
                )

                with (
                    mock.patch.object(base_tasks, "prepare_command_bounds", return_value=bounds),
                    mock.patch.object(base_tasks, "scaled_points", return_value={}),
                    mock.patch.object(base_tasks, "_run_global_rescue_subtask", side_effect=lambda *_: trace.append("global_rescue")),
                    mock.patch.object(base_tasks, "_run_battlefield_contest_subtask", side_effect=lambda *_: trace.append("battlefield_contest")),
                    mock.patch.object(base_tasks, "_run_element_trial_subtask", side_effect=lambda *_: trace.append("element_trial")),
                    mock.patch.object(base_tasks, "scroll_to_bottom", side_effect=lambda *_: trace.append("scroll")),
                    mock.patch.object(base_tasks, "_click_action", side_effect=lambda _args, _points, action, _bounds, **_kwargs: trace.append(action)),
                    mock.patch.object(base_tasks, "sleep_between"),
                ):
                    self.assertEqual(base_tasks.command_base_training_hall(args), 0)

                self.assertEqual(
                    trace[:6],
                    [
                        "global_rescue:started",
                        "base_tab",
                        "training_hall",
                        "global_rescue",
                        "global_rescue:completed",
                        "battlefield_contest:started" if bottom_task == "battlefield_contest" else "element_trial:started",
                    ],
                )
                self.assertEqual(trace[6:8], ["scroll", bottom_task])

    def test_legion_subset_navigates_after_reporting_selected_task_start(self) -> None:
        bounds = desktop_worker.common.Bounds("mock", "mock", 2, 33, 508, 949)
        trace: list[str] = []
        args = argparse.Namespace(
            from_task="shop",
            sweep_times=2,
            dry_run=False,
            backend="cgclick",
            desktop_task_ids=["shop"],
            desktop_navigate_legion=True,
            desktop_task_event=lambda task, status: trace.append(f"{task}:{status}"),
        )

        with (
            mock.patch.object(legion_tasks, "prepare_command_bounds", return_value=bounds),
            mock.patch.object(legion_tasks, "scaled_points", return_value={"legion_tab": (10, 20)}),
            mock.patch.object(legion_tasks, "perform_tab_click", side_effect=lambda *_: trace.append("navigate:legion") or "mock"),
            mock.patch.object(legion_tasks, "command_legion_shop_purchases", side_effect=lambda _args: trace.append("shop-handler") or 0),
        ):
            self.assertEqual(legion_tasks.command_legion_daily_rewards(args), 0)

        self.assertEqual(
            trace,
            ["shop:started", "navigate:legion", "shop-handler", "shop:completed"],
        )

    def test_run_finished_uses_stopped_for_cooperative_cancellation(self) -> None:
        plan = desktop_worker.build_daily_plan(["calendar"])
        events: list[dict[str, object]] = []

        def run_phase(phase: desktop_worker.DailyPhase, task_event) -> None:
            task_event("calendar", "started")
            raise desktop_worker.WorkerCancelled("stopped by user")

        status = desktop_worker.execute_daily_plan(plan, run_phase, events.append)

        self.assertEqual(status, "stopped")
        stopped_task = next(event for event in events if event["type"] == "task_finished")
        self.assertEqual(stopped_task["status"], "stopped")
        self.assertEqual(events[-1], {"type": "run_finished", "status": "stopped"})

    def test_daily_dry_run_reports_each_enabled_business_task(self) -> None:
        events: list[dict[str, object]] = []
        status = desktop_worker.run_request(
            {
                "mode": "daily",
                "task_ids": ["calendar", "welfare", "mail", "shop.special_pack_gold"],
                "from_task": "welfare",
                "dry_run": True,
            },
            events.append,
        )

        self.assertEqual(status, "dry_run_completed")
        self.assertEqual(
            [event["task_id"] for event in events if event["type"] == "task_started"],
            ["welfare", "mail", "shop.special_pack_gold"],
        )
        self.assertEqual(
            [event["task_id"] for event in events if event["type"] == "task_finished"],
            ["welfare", "mail", "shop.special_pack_gold"],
        )
        self.assertEqual(events[-1], {"type": "run_finished", "status": "dry_run_completed"})

    def test_default_daily_dry_run_matches_the_26_task_catalog_and_marks_gated_tasks_skipped(self) -> None:
        events: list[dict[str, object]] = []
        status = desktop_worker.run_request({"mode": "daily", "dry_run": True}, events.append)

        starts = [event["task_id"] for event in events if event["type"] == "task_started"]
        finishes = [event["task_id"] for event in events if event["type"] == "task_finished"]
        self.assertEqual(status, "partial")
        self.assertEqual(tuple(starts), desktop_worker.DAILY_TASK_IDS)
        self.assertEqual(tuple(finishes), desktop_worker.DAILY_TASK_IDS)
        armed_finished = next(event for event in events if event.get("task_id") == "armed.descent" and event["type"] == "task_finished")
        self.assertEqual(armed_finished["status"], "skipped")
        self.assertEqual(events[-1], {"type": "run_finished", "status": "partial"})

    def test_daily_passes_confirmed_reward_gates_in_route_order(self) -> None:
        events: list[dict[str, object]] = []
        status = desktop_worker.run_request(
            {
                "mode": "daily",
                "args": [
                    "--mechanical-shock-skip-animation-state", "checked",
                    "--mechanical-shock-task-claims", "0",
                    "--mechanical-shock-mech-fight-claim-state", "claimed",
                    "--pass-free-claim-state", "claimed", "--pass-work-plan-sign-state", "claimed",
                    "--armed-skip-animation-state", "checked", "--armed-free-draw-state", "claimed", "--armed-task-claims", "0",
                    "--mimic-skip-animation-state", "checked", "--mimic-free-draw-state", "claimed", "--mimic-task-claims", "0",
                    "--mimic-one-click-claim-state", "claimed",
                ],
                "dry_run": True,
            },
            events.append,
        )
        self.assertEqual(status, "dry_run_completed")
        started = [event["task_id"] for event in events if event["type"] == "task_started"]
        self.assertLess(started.index("patrol.claim"), started.index("mechanical.shock"))
        self.assertLess(started.index("mechanical.shock"), started.index("pass.daily"))
        self.assertLess(started.index("pass.daily"), started.index("armed.descent"))
        self.assertLess(started.index("patrol.claim"), started.index("armed.descent"))
        self.assertLess(started.index("armed.descent"), started.index("calendar"))
        self.assertLess(started.index("armed.descent"), started.index("mimic.card_library"))
        self.assertLess(started.index("mimic.card_library"), started.index("calendar"))
        mechanical_finished = next(event for event in events if event.get("task_id") == "mechanical.shock" and event["type"] == "task_finished")
        self.assertEqual(mechanical_finished["status"], "completed")
        armed_finished = next(event for event in events if event.get("task_id") == "armed.descent" and event["type"] == "task_finished")
        self.assertEqual(armed_finished["status"], "completed")

    def test_standalone_armed_command_without_gates_is_skipped(self) -> None:
        events: list[dict[str, object]] = []
        status = desktop_worker.run_request(
            {"mode": "command", "command": "armed-descent", "dry_run": True},
            events.append,
        )
        self.assertEqual(status, "partial")
        self.assertEqual(
            next(event for event in events if event["type"] == "task_finished")["status"],
            "skipped",
        )
        self.assertEqual(events[-1], {"type": "run_finished", "status": "partial"})

    def test_cli_run_emits_parseable_jsonl_dry_run_events(self) -> None:
        worker = Path(desktop_worker.__file__)
        request = {"mode": "daily", "task_ids": ["calendar", "mail"], "dry_run": True}
        result = subprocess.run(
            [sys.executable, str(worker), "run"],
            cwd=worker.parents[1],
            input=json.dumps(request) + "\n",
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertTrue(lines)
        events = [json.loads(line) for line in lines]
        self.assertEqual(events[-1], {"type": "run_finished", "status": "dry_run_completed"})
        self.assertEqual(
            [event["task_id"] for event in events if event["type"] == "task_started"],
            ["calendar", "mail"],
        )
        self.assertTrue(all(event["type"] != "log" or "{\"type\":" not in event.get("message", "") for event in events))

    def test_single_command_dry_run_emits_one_task_lifecycle(self) -> None:
        events: list[dict[str, object]] = []
        status = desktop_worker.run_request(
            {
                "mode": "command",
                "command": "patrol-full-from-home",
                "args": ["--quick-times", "2", "--ad-times", "1"],
                "dry_run": True,
            },
            events.append,
        )

        self.assertEqual(status, "dry_run_completed")
        self.assertEqual(events[0], {"type": "task_started", "task_id": "patrol-full-from-home"})
        self.assertEqual(
            next(event for event in events if event["type"] == "task_finished")["status"],
            "completed",
        )
        self.assertEqual(events[-1], {"type": "run_finished", "status": "dry_run_completed"})

    def test_windows_live_run_fails_before_any_input_action(self) -> None:
        with mock.patch.object(desktop_worker.sys, "platform", "win32"):
            with self.assertRaisesRegex(desktop_worker.WorkerError, "Windows 暂未实现"):
                desktop_worker.run_request(
                    {"mode": "daily", "task_ids": ["calendar"], "dry_run": False},
                    lambda _event: None,
                )


if __name__ == "__main__":
    unittest.main()
