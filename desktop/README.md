# 向僵尸开炮日常助手（macOS）

这是一个本机中文桌面面板，复用仓库已有任务目录，通过 Tauri 启动打包的 Python sidecar。默认开启模拟运行；脚本执行结束只说明任务流程结束，不代表游戏已确认领取奖励。

## 构建

首版 `.app` 需要在 macOS 上构建。准备 Node.js 22、Rust stable、Xcode Command Line Tools（提供 `clang`）和 Python 3。首次构建会在本目录建立 `.venv`，安装已固定版本的 PyInstaller，并把 Python runtime 打入 worker sidecar；运行后的 App 不调用仓库目录、Homebrew Python 或 clang。

### 首次设置本地签名

先在 `desktop/` 目录设置一次本机签名身份：

```sh
npm run setup:signing
```

脚本在当前用户的登录钥匙串中创建或复用名为 `Zombie Fire Daily Local Code Signing` 的自签名身份。只将证书的 `codeSign` 用途信任写入用户钥匙串；私钥不可导出，并限制为 `/usr/bin/codesign` 使用。身份指纹保存在 `~/Library/Application Support/向僵尸开炮日常助手/signing/identity.sha1`。脚本不会静默轮换证书；如果证书丢失、指纹不匹配或钥匙串无法访问，会停止并说明原因。macOS 可能显示钥匙串解锁或信任授权提示，请按系统提示处理；脚本不收集钥匙串密码。

这是仅供本机的签名，不是 Developer ID 签名，也没有公证，不能作为面向其他用户分发的安装包。首次改用该稳定身份后，若 macOS 为旧 ad-hoc 版本保存了辅助功能或自动化授权，需要从 `/Applications` 打开新版本，并在“辅助功能”及“自动化 → 系统事件”中重新授权一次。如果系统提示 `codesign` 使用签名私钥，请选择“始终允许”；“允许”只授权本次调用，后续签名可能再次提示。不要在聊天中提供钥匙串密码。之后每次升级都会复用同一证书及默认 designated requirement。本机已验证一次完整重建升级后，辅助功能与系统事件授权仍有效；这不保证更换签名身份或重装系统后授权仍保留。

### 日常升级

之后在 `desktop/` 目录使用一个命令构建、签名并安装：

```sh
npm run upgrade:macos
```

升级会先检查签名身份和所有路径下的助手/worker 进程，再运行完整构建。它拒绝覆盖运行中的自动化，不会结束进程。安装包先复制并验证到 `/Applications` 同卷暂存目录，再原子替换；旧 `.app` 会保留为带时间戳的 `.backup-*` 目录，用户配置仍保存在 `~/Library/Application Support/app.codex.zombiefire.daily/`。若复制或验证失败，会尝试恢复原安装。没有自动 `sudo` 或管理员权限回退；如果当前用户无法写入 `/Applications`，命令会失败并保留旧版本。

若 `/Applications` 已经安装了旧 ad-hoc 版本，首次切换时新旧 designated requirement 不同，常规升级会安全停止。请先手动将那一份旧包移动到 `/Applications` 中其他名称作为备份，再运行升级；不要删掉用户配置目录。当前没有旧安装时可以直接运行上面的命令。

需要核对两个构建时，可比较 app、worker 和输入 helper 的 designated requirement：

```sh
bash ./scripts/compare-macos-requirements.sh \
  "/path/to/旧版/向僵尸开炮日常助手.app" \
  "/path/to/新版/向僵尸开炮日常助手.app"
```

比较要求两边都通过 strict 签名验证，并拒绝仅绑定 `cdhash` 的 requirement。

自动安装步骤的失败保护测试可运行：

```sh
npm run test:macos-upgrade
```

该测试使用临时目录和替身签名校验，覆盖正在运行、requirement 改变、权限失败、暂存后校验失败及旧包回滚；不访问钥匙串、不执行真实构建或安装。

### 仅构建交付包

需要只生成本地 release 包而不安装时：

```sh
cd desktop
npm run build:app
```

此命令要求先设置本地签名身份，会重新打包 worker sidecar、Web 界面与 `.app`，但不会更改 `/Applications`。更新任务目录、参数或点击流程后，日常使用建议运行 `npm run upgrade:macos`。

交付包位于 `release/向僵尸开炮日常助手.app`。签名覆盖 worker、点击 helper 与整个 `.app`，并通过 strict 验证。应用的权限提示不会替您开启系统设置开关；系统事件授权通过只读查询检查，不代表辅助功能已授权。此应用不需要“屏幕录制”权限。请先保持“模拟运行”，确认游戏窗口和起始页面，再切换实时执行。

开发预览也使用相同的独立 worker：

```sh
cd desktop
npm ci
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python scripts/build-helper.py
npm run build:worker
npm run tauri -- dev
```

## 安全自检

构建 sidecar 后可以运行：

```sh
npm run self-test
# 也可以指定签名后的 .app 内 worker 做同一项安全模拟自检
npm run self-test -- "/absolute/path/向僵尸开炮日常助手.app/Contents/MacOS/zombie-fire-worker"
```

自检检查打包 worker 的任务目录，再以单条“日历礼包”命令运行模拟流程；它不会发送鼠标输入，也不会启动完整每日任务。

## 使用

- “每日任务”按游戏底部 Tab → 模块 → 任务三级展示，叶子始终按 `DAILY_TASK_IDS` 的业务顺序排列；可增删、启用或停用，并可从指定任务起跑。页面保留执行控制和起点，不单独维护任务参数。
- “单条命令”会按 worker 提供的参数目录生成选择器、数字输入和开关；入口页面会跟随 `--from-task` 选择变化。与日常阶段重叠的参数只保存一份，单条命令和每日阶段会读取同一值。
- App 参数表单默认领取状态为“可领取”、动画状态为“已勾选”，任务领取数为 3；普通/广告巡逻次数、军团扫荡次数、基地挑战次数和等待值沿用每日复合命令的现有默认值。它们是表单默认配置，不代表当前游戏页面状态；直接 CLI 的 gate 参数仍需显式提供，否则相应任务安全跳过。
- 通行证命令要求分别确认绿色免费“一键领取”和当天直免“签到”状态；留空会安全跳过对应点击并标记部分完成。周日下拉只沿作战计划左侧空边缘拖动一次，坐标为截图布局推断，尚未实机验证。
- 实时运行期间可使用界面停止按钮，或按 `⌃⌥⌘K` 请求停止。停止会先等待当前鼠标操作完成；进程未在宽限期内结束时，App 才会强制清理该次启动的进程组。
- 窗口默认不置顶，避免遮挡游戏和游戏内点击位置。需要时可点击右上角“置顶窗口”。
- 首页会分别显示辅助功能与 System Events 自动化权限。“检查权限”只读检查；“前往授权”在辅助功能未授权时会发出系统提示并打开辅助功能设置，已授权时会做有界只读的 System Events 检查，必要时可能触发 Apple Events 提示或打开自动化设置。系统不会替用户开启开关；实时任务启动前后端还会再次预检，任一项未就绪都不会启动计划。两项权限都已授权且读取无错误时，提示自动收起；异常状态仍显示。
- 中断后不会自动续跑。App 保存当前任务边界；重新开始时会从失败/停止任务开头重试，或在任务边界中断后选择下一项。
- 配置、进度和最近日志保存在 Tauri 用户数据目录（macOS：`~/Library/Application Support/app.codex.zombiefire.daily/`）。损坏配置可在界面中恢复；恢复前原始文件会复制为带时间戳的备份。

Windows 实时窗口识别和输入后端尚未实现。当前源码保留了可移植的界面与调度边界；未来 Windows 构建需补齐平台输入实现，并继续明确拒绝未支持的实时执行。
