import assert from "node:assert/strict";
import test from "node:test";
import {
  buildDailyPhaseArgs,
  groupCommandsByCategory,
  groupTasksByPhase,
  groupTasksByRoute,
  getCommandArgumentValue,
  migrateSharedCommandArgs,
  setCommandArgumentValue,
  shouldExpandPermissionNotice,
  shouldRenderPermissionNotice,
} from "../src/task-view-model.js";

test("consecutive tasks sharing a phase id render as one Chinese-labeled group", () => {
  const tasks = [
    { id: "patrol-claim", phase: "patrol" },
    { id: "patrol-quick", phase: "patrol" },
    { id: "calendar-claim", phase: "calendar" },
  ];

  assert.deepEqual(groupTasksByPhase(tasks), [
    { phaseId: "patrol", phase: "巡逻收益", tasks: tasks.slice(0, 2) },
    { phaseId: "calendar", phase: "日历礼包", tasks: tasks.slice(2) },
  ]);
});

test("route hierarchy preserves the supplied business task order across tabs", () => {
  const tasks = [
    { id: "patrol.claim", tab: "首页", module: "巡逻" },
    { id: "legion.daily_cut", tab: "军团", module: "军团日常" },
    { id: "patrol.ad_patrol", tab: "首页", module: "巡逻" },
    { id: "base.global_rescue", tab: "基地", module: "历练大厅" },
  ];

  const groups = groupTasksByRoute(tasks);
  assert.deepEqual(groups.map((tab) => tab.tab), ["首页", "军团", "首页", "基地"]);
  assert.deepEqual(groups.flatMap((tab) => tab.modules.flatMap((module) => module.tasks.map((task) => task.id))), tasks.map((task) => task.id));
  assert.equal(groups.at(-1).modules[0].module, "历练大厅");
});

test("command categories retain the first appearance order of the command catalog", () => {
  const groups = groupCommandsByCategory([
    { id: "daily-rewards", category: "daily" },
    { id: "patrol-full", category: "patrol" },
    { id: "mechanical-shock", category: "rewards" },
    { id: "calendar", category: "rewards" },
  ]);
  assert.deepEqual(groups.map((group) => group.categoryId), ["daily", "patrol", "rewards"]);
  assert.deepEqual(groups.at(-1).commands.map((command) => command.id), ["mechanical-shock", "calendar"]);
});

test("shared command arguments migrate without replacing explicit values and preserve zero and false", () => {
  const commands = [
    { id: "daily-rewards", args: [
      { name: "armed_task_claims", shared_key: "armed.task_claims", flag: "--armed-task-claims", type: "integer" },
      { name: "fit", shared_key: "window.fit", flag: "--fit", false_flag: "--no-fit", type: "boolean" },
    ] },
    { id: "armed-descent", args: [
      { name: "task_claims", shared_key: "armed.task_claims", flag: "--task-claims", type: "integer", default: 3 },
      { name: "backend", shared_key: "input.backend", flag: "--backend", type: "choice", default: "auto" },
    ] },
  ];
  const oldConfig = { last_command: "daily-rewards", command_args: {
    "daily-rewards": { armed_task_claims: "0", fit: false },
    "armed-descent": { task_claims: "2", backend: "quartz" },
  } };

  const migrated = migrateSharedCommandArgs(oldConfig, commands);
  assert.deepEqual(migrated.command_args.$shared, {
    "armed.task_claims": "0",
    "window.fit": false,
    "input.backend": "quartz",
  });
  assert.deepEqual(migrated.command_args["daily-rewards"], {});
  assert.deepEqual(migrated.command_args["armed-descent"], {});
  assert.deepEqual(migrateSharedCommandArgs({ command_args: { $shared: { "armed.task_claims": "1" }, "daily-rewards": { armed_task_claims: "0" } } }, commands).command_args.$shared, { "armed.task_claims": "1" });
});

test("editing one command stores a single shared value used by daily task arguments", () => {
  const commands = [
    { id: "armed-descent", args: [
      { name: "skip_animation_state", shared_key: "armed.skip_animation_state", choices: ["checked", "unchecked"], default: "checked", flag: "--skip-animation-state" },
      { name: "task_claims", shared_key: "armed.task_claims", type: "integer", default: 3, flag: "--task-claims" },
      { name: "backend", shared_key: "input.backend", choices: ["auto", "quartz"], default: "auto", flag: "--backend" },
    ] },
  ];
  const config = setCommandArgumentValue({ command_args: {} }, commands[0], "task_claims", "0");
  config.command_args.$shared["armed.skip_animation_state"] = "checked";
  config.command_args.$shared["input.backend"] = "quartz";

  assert.deepEqual(buildDailyPhaseArgs([{ id: "armed.descent", phase: "armed_descent" }], commands, config), {
    armed_descent: ["--skip-animation-state", "checked", "--task-claims", "0", "--backend", "quartz"],
  });
});

test("empty saved command values fall back to defaults while zero, false, and empty start values remain explicit", () => {
  const command = { id: "patrol-quick-batch", args: [
    { name: "times", shared_key: "patrol.quick_times", default: 3 },
    { name: "reward_wait", default: 0.5 },
    { name: "fit", default: true },
    { name: "from_task" },
    { name: "from_step" },
  ] };
  const config = { command_args: { $shared: { "patrol.quick_times": "" }, "patrol-quick-batch": {
    reward_wait: null, fit: false, from_task: "", from_step: null,
  } } };

  assert.equal(getCommandArgumentValue(config, command, command.args[0]), 3);
  assert.equal(getCommandArgumentValue(config, command, command.args[1]), 0.5);
  assert.equal(getCommandArgumentValue(config, command, command.args[2]), false);
  assert.equal(getCommandArgumentValue(config, command, command.args[3]), "");
  assert.equal(getCommandArgumentValue(config, command, command.args[4]), null);
});

test("permission notice hides only after both macOS permissions are granted", () => {
  assert.equal(shouldRenderPermissionNotice({ platform: "macos", accessibility: "granted", automation: "granted" }), false);
  assert.equal(shouldRenderPermissionNotice({ platform: "macos", accessibility: "granted", automation: "denied" }), true);
  assert.equal(shouldRenderPermissionNotice({ platform: "macos", accessibility: "granted", automation: "granted", error: "read failed" }), true);
  assert.equal(shouldRenderPermissionNotice({ platform: "macos", accessibility: "unavailable", automation: "timed_out" }), true);
});

test("permission notice collapses only for granted accessibility with unchecked automation", () => {
  assert.equal(shouldExpandPermissionNotice({ platform: "macos", accessibility: "granted", automation: "not_checked" }), false);
  assert.equal(shouldExpandPermissionNotice({ platform: "macos", accessibility: "granted", automation: "granted" }), true);
  for (const automation of ["denied", "needs_authorization", "timed_out", "unavailable"]) {
    assert.equal(shouldExpandPermissionNotice({ platform: "macos", accessibility: "granted", automation }), true);
  }
  assert.equal(shouldExpandPermissionNotice({ platform: "macos", accessibility: "granted", automation: "not_checked" }, "read failed"), true);
  assert.equal(shouldExpandPermissionNotice({ platform: "macos", accessibility: "denied", automation: "not_checked" }), true);
});
