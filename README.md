# zombie-fire-daily

`scripts/zombie_click.py` is the only CLI entry point. Shared safety, window,
scaling, timing, and click-backend code lives in `scripts/zombie_common.py`;
coordinates live in `scripts/zombie_actions.py`; tab workflows live under
`scripts/zombie_tasks/` (`patrol`, `battle_pass`, `armed`, `mimic`, `home`,
`legion`, `journey`, `base`, and twelve-phase `daily`). The entry point keeps
compatibility re-exports.

Use `--mock-bounds ... --dry-run` for planning output only: mock runs do not
focus windows, click, or prove that a reward was received.

## 桌面 App

`desktop/` 使用 Tauri + Python sidecar。中文面板提供单条命令、每日任务增删、启用/禁用、指定起点、日志和停止功能。首版交付 macOS，Windows 自动化后端后续独立适配；详见 [桌面构建与使用说明](desktop/README.md)。

每日计划以 Tab → 模块 → 任务展示，同时保持 `DAILY_TASK_IDS` 的执行顺序。单条命令与对应日常阶段共享同一份已保存参数；App 表单默认与 CLI 的显式 gate 安全规则分别见桌面说明和 `SKILL.md`。

```sh
cd desktop
npm run setup:signing    # 首次设置本机签名身份
npm run upgrade:macos    # 构建、签名并安装到 /Applications
```

项目代码编写遵循 `AGENTS.md`：使用 `gpt-6-luna`，推理强度 `xhigh`。
