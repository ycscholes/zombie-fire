# Tauri + Python 桌面 App Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development; code writing uses gpt-6-luna with xhigh. Work in this checkout, never Git worktrees.

**Goal:** 交付支持单命令、可增删每日任务、停止及指定任务起点的 macOS App。
**Architecture:** Tauri 2 原生壳 + 本地 Web 界面 + Python 独立 sidecar。双方采用 JSON lines 协议；平台输入与共享业务分离。
**Tech Stack:** Tauri 2 / Rust / TypeScript or vanilla JavaScript / Python / PyInstaller。

## Files and contract
Python implementation owns `scripts/desktop_worker.py`, `scripts/test_desktop_worker.py` and narrowly scoped task changes. Desktop implementation owns `desktop/` including frontend, Rust commands, packaging and usage docs. Existing dirty legion change is preserved.

Worker calls: `desktop_worker.py catalog` prints one JSON document; `desktop_worker.py run` accepts a JSON request on stdin. Request: `{mode: "daily"|"command", task_ids: string[], from_task: string|null, command: string, args: string[], dry_run: bool}`. Run emits JSON lines `{type: "log"|"task_started"|"task_finished"|"run_finished"|"error", message?: string, task_id?: string, status?: string}`. catalog includes commands with argument metadata and daily tasks with id/name/entry_page; one shared authoritative directory. Worker exits nonzero on failures; task completion means execution only.

## Task 1: Execution engine
- [x] Add focused tests for enabled task selection, starting suffix, invalid ids/args, failure stopping subsequent tasks and event emission.
- [x] Reuse 22 existing tasks, add required navigation when earlier tasks are removed, preserve default route and nested ordering.
- [x] Implement catalog and command execution via existing argparse, arguments as arrays. No arbitrary shell commands.
- [x] Implement cancellation with no further inputs and child process cleanup; macOS backend stays current, unsupported Windows live execution fails clearly.
- [x] Run worker tests and all existing tests; classify pre-existing gift-return failure.

## Task 2: Desktop shell and interface
- [x] Build local Chinese interface with single command parameter controls, editable daily enabled list, resume selector and entry-page notice.
- [x] Add Rust commands for catalog/run/stop, lock single process, stream JSON events to UI, bounded logs, clean termination on app close.
- [x] Persist config and current task atomically in app data; malformed config has recovery UI, unfinished progress is shown on restart.
- [x] Bundle Python worker and runtime using sidecar resources. Current app must run without relying on this repository path or Homebrew Python.
- [x] Build app with reproducible build command and instructions. Preserve Windows build/backend boundary.

## Task 3: Review and validation
- [x] Main coordinator reviews spec and quality; fixes are assigned to gpt-6-luna xhigh.
- [x] Check full daily dry-run, subsets, starting task, single commands, concurrency, stop, error events and restart persistence.
- [x] Launch packaged app and inspect actual UI. Exercise dry-run flows through app, verify independent packaged resources.
- [x] Document test evidence and limits; deliver clickable .app path. No automatic live reward run.

## Baseline and decisions
88 existing unittest tests: 87 passed, one gift-return expected sequence stale against existing dirty legion code. No app yet. Keep default fixed order; add/remove means choosing existing task catalog, not recording new coordinates. User-selected Tauri supersedes previous Qt recommendation. No push, merge or release requested.
