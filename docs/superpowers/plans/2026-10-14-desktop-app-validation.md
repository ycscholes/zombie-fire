# 桌面 App 验收记录

## 需求与证据
| 要求 | 待核实证据 |
| --- | --- |
| 单独命令执行 | 打包 worker catalog + App 参数界面 + App 无点击执行日志 |
| 默认每日范围 | 当前 22 个业务任务与执行计划逐项对应 |
| 自主添加删减 | 界面增删后 plan 与持久化内容一致，不执行删除的奖励 |
| 开始与停止 | 单进程限制、停止终态、退出不遗留子进程 |
| 指定起点恢复 | 从启用任务后缀执行、入口页面提示、保存当前任务、重启中断提示 |
| 可运行 app | 本机构建与启动、打包 Python 无仓库路径依赖、权限说明 |
| Windows 扩展 | 共享 UI/协议、平台后端边界、不误称 Windows 已可用 |
| 模型执行规则 | AGENTS.md + 代码实施代理 gpt-6-luna xhigh |

## 已确认基线
- 当前 macOS 26.6.2 / Apple Silicon，Node 22 已安装。
- 初始 unittest：88 项，87 通过，1 项已有 gift-return 测试预期失配。
- 当前 legion.py 未提交更改保留；AGENTS.md 原本未跟踪。
- 不执行游戏真实领奖流程；可运行性与自动化领奖成功分开报告。

## 运行验证
后续记录实际命令、退出码、UI 观察和打包路径；未验证项不标记为完成。

## 第一轮 Python 审查
独立审查代理通过无点击复现确认：真实执行预检查/清理输出未纳入 JSONL、删除 terminal_crisis 后底部训练项目缺滚动、failed/stopped 回调未阻断后续任务。已交给 gpt-6-luna xhigh 实施代理修复并补测试；不能以当时 10 项 worker 测试通过判定完成。

## 桌面生命周期审查
协调代理指出：主窗口置顶可能遮挡真实点击、退出时须协作停止并留出鼠标抬起时间、成功事件必须同时校验进程退出码、损坏配置不能在恢复前覆盖。桌面实施代理正在补齐上述边界。

## Python 当前验证（2026-10-14）
- `python3 -m unittest scripts.test_desktop_worker -q`：17 项通过。
- `python3 -m unittest discover -s scripts -p 'test_*.py'`：105 项通过；已有军团礼物返回行为的旧测试预期已更新，原行为保留。
- 实际 `desktop_worker.py run` 默认每日模拟：66 行合法 JSONL，22 个 task_started/task_finished，最后为 dry_run_completed。
- 独立审查复核三项修复均已解决；只证明无点击执行协议与路由逻辑，不证明游戏领奖结果。
- Rust stable 1.99.0 安装完成，尚待桌面编译与打包验证。

## 独立打包组件验证
- 最新全量 Python 回归：108 项通过。
- 使用 `env -i PATH=/usr/bin:/bin TMPDIR=/tmp`、工作目录 `/tmp` 启动打包 worker：catalog 为 25 命令、22 每日任务。
- 同一受限环境每日子集恢复：从 base.global_expedition 开始，实际事件仅为 base.global_expedition、base.element_trial、shop.special_pack_gold；终态 dry_run_completed。
- Vite 构建与 packaged worker 的 stdin 保持打开自检已由实施代理跑通；协调代理独立复核进行中。

## 桌面复核
Vite production build 与独立 sidecar self-test 已由协调代理实际重跑通过；sidecar 在 stdin 保持打开时正常自行退出。
五项原生/前端生命周期问题在独立源码复核中已解决（启动事件顺序、双击锁、失败计数、入口页映射、结束状态持久化）。启动中的停止锁存仍需最后修正与复核，不能据此宣称 App 已交付。

## 最后停止竞态复核
独立审查确认：前端取消配置保存阶段的启动、stop_run 返回 false 时补发；后端在同一 process 锁中检查 gate 并转交停止 latch，已取消的 idle worker 不接收任务请求。对应 WorkerStopState 三种时序测试已加入，待 cargo 实际执行。此范围源码复核无未解决项。

## 最终原生 App 验收
- 当前 macOS / Apple Silicon .app 已实际启动，页面 URL 为 tauri://localhost；8 阶段与 22 项任务正确显示，开始/停止在首屏。
- App 完整每日模拟完成 22/22；删除广告巡逻与福利、从日历起点运行时实际日志仅包含 18 项，终态 dry_run_completed。
- App 单条完整巡逻命令模拟完成 1/1，参数控件与运行方式可见。
- 启动后全局停止快捷键：终态 stopped、业务 task_started 为空、无残留 worker。
- 已执行受控模拟进程强制中断并重启：显示“上次运行在日历礼包期间中断”、不自动运行，配置仍保留 20 项和日历起点；随后实际添加任务成功，并恢复 22 项默认计划及模拟开关。
- 窗口实时模式的外部变更曾触发启动尝试；窗口聚焦校验失败并结束，日志未显示游戏输入投递。没有验证真实游戏奖励领取或完整现场路线。
- 最后父进程断开修复：live run 在 stdin EOF 请求协作停止；dry-run EOF 保持原行为。最终 Python 全量 109 项、Rust 8 项、界面模型与 release 配置测试、打包 sidecar 自检通过。
- 最终打包 worker SHA-256：866d9fc66e3e2c049e0b2d91b5f7d658001d6c2655f22ad3e4ddb42fe6d96104，与源 sidecar 一致。Info.plist 检查通过。
- 稳定交付路径：desktop/release/向僵尸开炮日常助手.app；副本与最终 bundle 递归比较相同。

## 边界
首版仅在当前 macOS Apple Silicon 机器验证；Windows 保留界面/协议复用与平台输入边界，尚未提供 Windows 实时执行与实机校准。真实执行需要游戏页面与辅助功能/自动化权限准备就绪。

## 交付副本最后检查
稳定目录副本已实际启动并呈现完整默认计划；从副本启动模拟后退出，worker 已被清理，无后台执行进程。运行中退出后若记录仍处于运行状态，下一次打开按中断任务边界恢复，不自动运行。测试后保留模拟模式与 22 项默认配置。
