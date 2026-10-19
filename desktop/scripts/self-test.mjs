import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { isAbsolute, join } from "node:path";
import { fileURLToPath } from "node:url";
import { groupTasksByRoute } from "../src/task-view-model.js";

// 以默认 sidecar 或命令行指定的 worker 执行安全模拟命令，并验证 JSONL 生命周期。
const scriptDir = fileURLToPath(new URL(".", import.meta.url));
const desktopRoot = join(scriptDir, "..");
const architecture = process.arch === "arm64" ? "aarch64" : process.arch === "x64" ? "x86_64" : null;
assert.ok(architecture, `当前架构 ${process.arch} 不在 macOS self-test 支持范围内`);
const targetTriple = `${architecture}-apple-darwin`;
const workerPath = process.argv[2] ?? join(desktopRoot, "src-tauri", "binaries", `zombie-fire-worker-${targetTriple}`);

assert.equal(process.platform, "darwin", "sidecar self-test 当前仅支持 macOS");
assert.ok(isAbsolute(workerPath), `worker 路径必须是绝对路径：${workerPath}`);
assert.ok(existsSync(workerPath), `缺少打包的 worker：${workerPath}，先运行 npm run build:worker`);

function collectCatalog() {
  return new Promise((resolve, reject) => {
    const child = spawn(workerPath, ["catalog"], { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8").on("data", (chunk) => { stdout += chunk; });
    child.stderr.setEncoding("utf8").on("data", (chunk) => { stderr += chunk; });
    child.once("error", reject);
    child.once("close", (code) => {
      if (code !== 0) reject(new Error(`catalog 退出码 ${code}：${stderr}`));
      else {
        try { resolve(JSON.parse(stdout)); } catch (error) { reject(error); }
      }
    });
  });
}

function dryRunCalendar() {
  return new Promise((resolve, reject) => {
    const child = spawn(workerPath, ["run"], { stdio: ["pipe", "pipe", "pipe"] });
    const events = [];
    let stdout = "";
    let stderr = "";
    let settled = false;
    const timeout = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill("SIGKILL");
      reject(new Error(`模拟运行超时；worker 未在 stdin 保持打开时自行退出。输出：${stderr}`));
    }, 20000);
    child.stdout.setEncoding("utf8").on("data", (chunk) => {
      stdout += chunk;
      const lines = stdout.split("\n");
      stdout = lines.pop() ?? "";
      for (const line of lines) {
        if (line.trim()) events.push(JSON.parse(line));
      }
    });
    child.stderr.setEncoding("utf8").on("data", (chunk) => { stderr += chunk; });
    child.once("error", (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      reject(error);
    });
    child.once("close", (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      if (stdout.trim()) events.push(JSON.parse(stdout.trim()));
      const terminal = events.findLast((event) => event.type === "run_finished");
      try {
        assert.equal(code, 0, `worker 退出码 ${code}：${stderr}`);
        assert.ok(events.some((event) => event.type === "task_started" && event.task_id === "calendar-claim"));
        assert.ok(events.some((event) => event.type === "task_finished" && event.task_id === "calendar-claim" && event.status === "completed"));
        assert.equal(terminal?.status, "dry_run_completed");
        resolve(events);
      } catch (error) {
        reject(error);
      }
    });
    child.stdin.write(`${JSON.stringify({
      mode: "command",
      task_ids: [],
      from_task: null,
      command: "calendar-claim",
      args: [],
      dry_run: true,
    })}\n`);
    // 故意保持 stdin 打开：验证 PyInstaller one-file sidecar 不会被控制读线程卡住退出。
  });
}

const catalog = await collectCatalog();
assert.ok(catalog.commands.some((command) => command.id === "calendar-claim"));
assert.ok(catalog.commands.some((command) => command.id === "battle-pass-daily"));
assert.equal(catalog.daily_tasks.length, 26);
assert.deepEqual(
  catalog.daily_tasks.slice(0, 7).map((task) => task.id),
  ["patrol.claim", "patrol.quick_patrol", "patrol.ad_patrol", "mechanical.shock", "pass.daily", "armed.descent", "mimic.card_library"],
);
const groups = groupTasksByRoute(catalog.daily_tasks);
assert.deepEqual(
  groups.flatMap((tab) => tab.modules.flatMap((module) => module.tasks.map((task) => task.id))),
  catalog.daily_tasks.map((task) => task.id),
);
assert.equal(groups.at(-1)?.tab, "商城");
const patrol = catalog.commands.find((command) => command.id === "patrol-full-from-home");
assert.equal(patrol?.entry_pages?.quick_patrol, "巡逻面板");
const baseHall = catalog.commands.find((command) => command.id === "base-training-hall");
assert.equal(baseHall?.entry_pages?.deep_abyss, "训练大厅列表");
const events = await dryRunCalendar();
console.log(`Sidecar self-test passed: ${catalog.commands.length} commands, ${catalog.daily_tasks.length} daily tasks, ${events.length} JSONL events.`);
