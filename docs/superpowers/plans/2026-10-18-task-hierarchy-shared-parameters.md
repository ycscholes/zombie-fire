# Task hierarchy and shared parameters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现已确认的三级任务展示、共享参数、默认可领取与授权提示收起。

**Architecture:** 复用 worker 业务目录和 CLI 参数定义。单条命令配置经同一参数映射进入日常执行请求，避免日常独立 gate 状态；界面模型按原始业务顺序构造三级树。

**Tech Stack:** 现有 Tauri 2、原生 JS/CSS、Python worker，无新增依赖。

**Spec:** docs/superpowers/specs/2026-10-18-task-hierarchy-shared-parameters.md

## Global Constraints

- 实现与测试代码仅由 gpt-6-luna、xhigh 编写；协调代理负责审查验证。
- 保留所有先前改动，不提交无关内容，不建 worktree，不执行真实游戏任务。
- App 所有领取状态默认 available，任务领奖数量默认 3，动画默认 checked；共享参数以日常复合命令为默认来源，保留显式配置值。直接 CLI 缺 gate 仍安全跳过。
- 共享值必须到达实际执行层，不能仅显示一致。

## Review Focus

- 混合 Tab/模块输入仍保留叶任务业务顺序。
- 单条命令显式选择 claimed、0 和 false 不被默认值覆盖。
- 复合命令参数名与单任务不同，映射后值仍一致。
- 旧配置迁移不丢失用户选择，日常无独立属性表单。
- 两项授权仅一项 granted 或状态检查失败时提示仍可见。

### Task 1: 参数统一与真实执行

**Files:** scripts/desktop_worker.py、scripts/zombie_click.py、相关任务模块、desktop/src/main.js、必要的共享参数模块、对应 Python/JS 测试。

- [x] 为默认、显式覆盖、旧配置及复合映射添加回归测试。
- [x] 将任务到单命令的参数映射在执行请求和 worker 中贯通，同步 Rust 请求结构；保留既有安全检查。
- [x] 去掉日常 gate 状态和命令临时重置，确保持久配置为唯一来源。
- [x] 运行聚焦 Python/JS 测试，验证 actual handler 接收同样参数。

### Task 2: 界面层级与权限

**Files:** desktop/src/task-view-model.js、desktop/src/main.js、desktop/src/styles.css、desktop/scripts/task-view-model.test.mjs。

- [x] 添加三级分组顺序及双授权显示规则测试。
- [x] 显示 Tab→模块→叶任务，移除日常属性表单，保留执行控制和起点。
- [x] 两项授权均 granted 时隐藏提示，辅助功能已授权而自动化尚未检查时默认收起，异常仍展开显示。
- [x] 运行 UI 模型测试与前端构建。

### Task 3: 文档与交付验证

**Files:** SKILL.md、受影响的 README、desktop/release/向僵尸开炮日常助手.app。

- [x] 更新默认可领取和参数共用规则，修订冲突说明。
- [x] 运行全部适用 Python 测试、UI 模型测试、Rust 请求结构测试及前端构建。
- [x] 重建 sidecar 和 App，以打包 worker 进行安全模拟 self-test，检查签名。
- [x] 分开记录测试、打包和实际游戏验证状态，提供可打开的 App 路径。

## 最终验证记录

- Python 全量 120 项、UI 模型 8 项、Rust 全量 16 项均通过；前端 build、release-config、SKILL quick_validate 与 diff 检查通过。
- 已重建 sidecar 和 App，稳定本地签名 strict 验证通过，app/worker/helper 的 designated requirements 与此前安装一致。
- 已安装到 `/Applications/向僵尸开炮日常助手.app`，最终安装包 self-test 返回 29 commands、26 daily tasks、4 JSONL events。
- 用 Computer Use 打开最终安装版本，确认日常右侧仅保留控制和起点，三级结构中基地→历练大厅→具体任务顺序正确，自动化待检查提示默认收起，命令页通行证状态默认可领取/可签到。
- 本次未执行真实游戏领取；游戏业务领取结果未验证。CLI 既有缺 gate 安全跳过规则保留。
