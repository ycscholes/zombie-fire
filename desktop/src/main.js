import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { buildDailyPhaseArgs, getCommandArgumentValue, groupCommandsByCategory, groupTasksByPhase, groupTasksByRoute, migrateSharedCommandArgs, PHASE_NAMES, PHASE_ORDER, setCommandArgumentValue, shouldExpandPermissionNotice, shouldRenderPermissionNotice } from "./task-view-model.js";
import "./styles.css";

const state = {
  catalog: null,
  config: { enabled_task_ids: [], daily_start_task_id: null, last_command: null, command_args: {}, dry_run: true },
  progress: null,
  configError: null,
  permissions: null,
  permissionBusy: false,
  permissionError: null,
  selectedView: "daily",
  selectedCommandId: null,
  selectedTaskPhase: "all",
  isRunning: false,
  stopRequested: false,
  pendingStopRequested: false,
  stopDispatchIssued: false,
  stopRetryUsed: false,
  startPhase: null,
  onTop: false,
  activeRunId: null,
  completedTaskIds: [],
  runPlanCount: 0,
  logs: [],
  error: null,
};

const byId = (id) => document.getElementById(id);
const ARG_LABELS = {
  times: "执行次数",
  quick_times: "普通快速巡逻次数",
  ad_times: "广告快速巡逻次数",
  battle_times: "挑战次数",
  panel_wait: "打开面板等待（秒）",
  claim_wait: "领取后等待（秒）",
  dismiss_wait: "关闭弹窗等待（秒）",
  quick_reward_wait: "巡逻奖励等待（秒）",
  quick_between: "快速巡逻间隔（秒）",
  ad_wait: "广告等待（秒）",
  ad_close_wait: "广告关闭等待（秒）",
  ad_reward_wait: "广告奖励等待（秒）",
  ad_between: "广告巡逻间隔（秒）",
  reward_wait: "奖励等待（秒）",
  confirm_wait: "确认等待（秒）",
  close_wait: "关闭等待（秒）",
  menu_wait: "菜单等待（秒）",
  open_wait: "打开页面等待（秒）",
  between: "步骤间隔（秒）",
  backend: "输入后端",
  fit: "自动调整游戏窗口",
  from_task: "从子任务开始",
  from_step: "每日流程起始阶段",
  armed_skip_animation_state: "武装降临跳过动画状态（本次确认）",
  armed_free_draw_state: "武装降临免费抽取状态（本次确认）",
  armed_task_claims: "武装降临当前首行可领奖数（本次确认）",
  mechanical_shock_skip_animation_state: "机械震荡跳过动画状态（本次确认）",
  mechanical_shock_task_claims: "机械震荡当前首行可领奖数（本次确认）",
  mechanical_shock_mech_fight_claim_state: "机甲械斗一键领取状态（本次确认）",
  pass_free_claim_state: "通行证绿色一键领取状态（本次确认）",
  pass_work_plan_sign_state: "当天作战计划直免签到状态（本次确认）",
  free_claim_state: "通行证绿色一键领取状态（本次确认）",
  work_plan_sign_state: "当天作战计划直免签到状态（本次确认）",
  mimic_skip_animation_state: "拟态牌库跳过动画状态（本次确认）",
  mimic_free_draw_state: "拟态牌库免费抽取状态（本次确认）",
  mimic_task_claims: "拟态牌库当前首行可领奖数（本次确认）",
  mimic_one_click_claim_state: "拟态牌库红点一键奖励状态（本次确认）",
  skip_animation_state: "跳过动画复选框状态（本次确认）",
  free_draw_state: "免费抽取状态（本次确认）",
  task_claims: "当前首行可领奖数（本次确认）",
  reward_page_wait: "奖励页面等待（秒）",
  skip_scroll: "跳过列表滚动",
  sweep_times: "扫荡次数",
  sweep_between: "扫荡间隔（秒）",
  sweep_reward_wait: "扫荡奖励等待（秒）",
};
const BACKEND_NAMES = {
  auto: "自动选择",
  cgclick: "CGEvent 助手",
  quartz: "Quartz",
  cliclick: "cliclick",
  "system-events": "System Events",
};
const TASK_CHOICE_NAMES = {
  claim: "领取巡逻收益",
  quick_patrol: "普通快速巡逻",
  ad_patrol: "广告快速巡逻",
  cafeteria: "基地食堂",
  global_rescue: "寰球救援",
  global_expedition: "寰球远征",
  deep_abyss: "深渊挑战",
  terminal_crisis: "末日危机",
  battlefield_contest: "巅峰争霸",
  element_trial: "元素试炼",
  shop: "玩法商店采购",
  resources: "征途资源",
  purifier: "净化者招募",
  daily_cut: "军团每日一刀",
  foreign_rewards: "军团异域挑战奖励",
  shop_purchases: "军团商店采购",
  journey_gifts: "军团征途礼物",
  "pass.daily": "通行证与作战计划签到",
  "mechanical.shock": "机械震荡",
  "mimic.card_library": "拟态牌库",
  gift_claim: "领取征途礼物",
  expedition: "征途远征",
  gun_blueprint: "枪械蓝图",
  base_powder: "基地火药",
  enhancer: "强化剂",
  resource_gold: "商城资源金币",
  special_pack_gold: "特惠礼包金币",
};
const tasks = () => state.catalog?.daily_tasks ?? [];
const commands = () => state.catalog?.commands ?? [];
const enabledTasks = () => tasks().filter((task) => state.config.enabled_task_ids.includes(task.id));
const selectedStartTask = () => enabledTasks().find((task) => task.id === state.config.daily_start_task_id) ?? enabledTasks()[0] ?? null;
const chosenCommand = () => commands().find((command) => command.id === state.selectedCommandId) ?? commands()[0] ?? null;

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

function statusLabel() {
  if (state.isRunning && state.stopRequested) return "正在停止";
  if (state.isRunning) return "执行中";
  const status = state.progress?.status;
  return ({ completed: "已结束", partial: "部分完成", dry_run_completed: "模拟完成", failed: "执行失败", stopped: "已停止", interrupted: "上次中断" })[status] ?? "就绪";
}

function statusTone() {
  if (state.isRunning) return state.stopRequested ? "amber" : "green";
  return ({ failed: "red", interrupted: "amber", stopped: "muted", completed: "green", partial: "amber", dry_run_completed: "amber" })[state.progress?.status] ?? "muted";
}

function interruptionNotice() {
  if (state.progress?.status !== "interrupted") return "";
  const current = tasks().find((item) => item.id === state.progress.current_task_id);
  const lastFinished = tasks().find((item) => item.id === state.progress.last_finished_task_id);
  const next = lastFinished
    ? enabledTasks().find((item) => tasks().findIndex((task) => task.id === item.id) > tasks().findIndex((task) => task.id === lastFinished.id))
    : null;
  const target = current ?? next;
  const context = current
    ? `上次运行在「${current.name}」期间中断`
    : lastFinished
      ? `上次运行在「${lastFinished.name}」完成后中断`
      : "上次运行期间中断";
  const actionLabel = current ? "从这里开始" : "从下一项继续";
  return `<section class="notice notice-warn"><div><strong>${escapeHtml(context)}</strong><p>没有自动续跑。所选任务会从任务开头重新执行。</p></div><button class="button button-small" data-action="resume-from-last" data-task-id="${escapeHtml(target?.id || "")}" ${target && !state.configError ? "" : "disabled"}>${actionLabel}</button></section>`;
}

function configNotice() {
  if (!state.configError) return "";
  return `<section class="notice notice-error"><div><strong>配置文件无法读取</strong><p>${escapeHtml(state.configError)}。原文件已保留；恢复默认时会先另存一份。</p></div><button class="button button-small" data-action="restore-defaults">恢复默认配置</button></section>`;
}

function permissionStateLabel(value) {
  return ({
    granted: "已授权",
    denied: "未授权",
    needs_authorization: "需授权",
    not_checked: "尚未检查",
    timed_out: "检查超时",
    unavailable: "无法检查",
    unsupported: "不适用",
  })[value] ?? "状态未知";
}

function renderPermissions() {
  const permissions = state.permissions;
  if (!shouldRenderPermissionNotice(permissions, state.permissionError)) return "";
  if (permissions?.platform !== "macos" && !state.permissionError) return "";
  const accessibility = permissionStateLabel(permissions?.accessibility);
  const automation = permissionStateLabel(permissions?.automation);
  const summaryAutomation = permissions?.automation === "not_checked" ? "待检查" : automation;
  return `<details class="notice permission-notice" aria-labelledby="permission-title" ${shouldExpandPermissionNotice(permissions, state.permissionError) ? "open" : ""}>
    <summary class="permission-summary">macOS授权 · 辅助功能${escapeHtml(accessibility)} · 自动化${escapeHtml(summaryAutomation)}</summary>
    <div class="permission-details"><div class="permission-copy"><strong id="permission-title">macOS 系统授权</strong>
      <p>辅助功能输入与控制“系统事件”的自动化是两项独立授权；辅助功能已授权不代表自动化可用。</p>
      <div class="permission-statuses"><span><b>辅助功能</b><em class="permission-${escapeHtml(permissions?.accessibility || "unavailable")}">${escapeHtml(accessibility)}</em></span><span><b>System Events 自动化</b><em class="permission-${escapeHtml(permissions?.automation || "unavailable")}">${escapeHtml(automation)}</em></span></div>
      ${permissions?.automation === "not_checked" ? `<p>检查不会请求授权；若 System Events 尚未运行，状态会显示“尚未检查”。实时启动会再次预检。</p>` : ""}
      ${permissions?.automation === "needs_authorization" || permissions?.automation === "denied" ? `<p>请在系统设置 → 隐私与安全性 → 自动化中允许此应用控制 System Events；此授权与辅助功能相互独立。</p>` : ""}
      ${permissions?.automation === "timed_out" ? `<p>System Events 查询超时；可点“前往授权”打开对应设置页，再手动检查授权状态。</p>` : ""}
      ${state.permissionError ? `<p class="permission-error">${escapeHtml(state.permissionError)}</p>` : ""}
    </div>
    <div class="permission-actions"><button class="button button-small" data-action="check-permissions" ${state.permissionBusy ? "disabled" : ""}>${state.permissionBusy ? "正在检查…" : "检查权限"}</button><button class="button button-small button-secondary" data-action="request-permissions" ${state.permissionBusy ? "disabled" : ""}>前往授权</button></div>
    <p class="permission-footnote">“前往授权”会请求辅助功能授权；若辅助功能已就绪，也会检查 System Events 自动化并按需打开对应设置。系统不会替您开启开关；完成后点“检查权限”刷新。</p></div>
  </details>`;
}

function renderDaily() {
  const groups = groupTasksByRoute(tasks());
  const enabled = new Set(state.config.enabled_task_ids);
  const selected = selectedStartTask();
  const fromIndex = selected ? enabledTasks().findIndex((task) => task.id === selected.id) : 0;
  const runCount = Math.max(0, enabledTasks().length - fromIndex);
  const selectedIndex = selected ? tasks().findIndex((task) => task.id === selected.id) : -1;
  const sourceAfterStart = selectedIndex >= 0 ? tasks().slice(selectedIndex).filter((task) => enabled.has(task.id)) : [];
  const available = tasks().filter((task) => !enabled.has(task.id));
  const phaseCounts = new Map(PHASE_ORDER.map((phaseId) => [phaseId, { total: 0, enabled: 0 }]));
  for (const task of tasks()) {
    const count = phaseCounts.get(task.phase);
    if (count) {
      count.total += 1;
      if (enabled.has(task.id)) count.enabled += 1;
    }
  }
  const allEnabledCount = enabledTasks().length;
  const phaseFilters = [
    { id: "all", name: "全部", count: { enabled: allEnabledCount, total: tasks().length } },
    ...PHASE_ORDER.map((phaseId) => ({ id: phaseId, name: PHASE_NAMES[phaseId], count: phaseCounts.get(phaseId) })),
  ].map((phase) => `<button type="button" class="phase-filter ${state.selectedTaskPhase === phase.id ? "phase-filter-active" : ""}" data-phase-filter="${escapeHtml(phase.id)}" aria-pressed="${state.selectedTaskPhase === phase.id}"><span>${escapeHtml(phase.name)}</span><small>${phase.count.enabled}/${phase.count.total}</small></button>`).join("");
  const renderTask = (task) => {
    const isEnabled = enabled.has(task.id);
    const isStart = selected?.id === task.id;
    return `<label class="task-row ${isEnabled ? "" : "task-off"} ${isStart ? "task-start" : ""}">
      <input type="checkbox" data-task-toggle="${escapeHtml(task.id)}" ${isEnabled ? "checked" : ""} ${state.isRunning || state.configError ? "disabled" : ""} />
      <span class="task-check" aria-hidden="true"></span>
      <span class="task-copy"><span class="task-name">${escapeHtml(task.name)}</span><span class="task-entry">${escapeHtml(task.entry_page || "页面信息待补充")}</span></span>
      ${isStart ? `<span class="start-mark">起点</span>` : ""}
    </label>`;
  };
  const rows = groups.map((tab, tabIndex) => {
    const modules = tab.modules.map((module, moduleIndex) => {
      const visibleTasks = module.tasks.filter((task) => state.selectedTaskPhase === "all" || task.phase === state.selectedTaskPhase);
      if (!visibleTasks.length) return "";
      const moduleTasks = module.tasks.map((task) => task.id);
      const selectedCount = moduleTasks.filter((id) => enabled.has(id)).length;
      return `<section class="route-module">
        <div class="route-module-heading"><span class="phase-index">${String(tabIndex + 1).padStart(2, "0")}.${moduleIndex + 1}</span><span>${escapeHtml(module.module)}</span><span class="phase-count">${selectedCount}/${moduleTasks.length}</span><span class="phase-heading-actions"><button type="button" class="phase-action" data-action="route-tasks" data-task-ids="${escapeHtml(moduleTasks.join(","))}" data-task-mode="all" aria-label="${escapeHtml(module.module)}全选" ${state.isRunning || state.configError ? "disabled" : ""}>全选</button><button type="button" class="phase-action" data-action="route-tasks" data-task-ids="${escapeHtml(moduleTasks.join(","))}" data-task-mode="clear" aria-label="清空${escapeHtml(module.module)}" ${state.isRunning || state.configError ? "disabled" : ""}>清空</button></span></div>
        <div class="task-list">${visibleTasks.map(renderTask).join("")}</div>
      </section>`;
    }).join("");
    if (!modules) return "";
    return `<section class="route-tab"><div class="route-tab-heading">${escapeHtml(tab.tab)}</div>${modules}</section>`;
  }).join("");

  return `<div class="workspace-grid">
    <section class="panel planner-panel">
      <div class="panel-head">
        <div><div class="eyebrow">DAILY ROUTINE / ${tasks().length} TASKS</div><h2>每日任务计划</h2><p class="panel-subtitle">现有业务任务按固定流程排列；勾选用于组合与裁剪，不支持改写任务步骤。</p></div>
        <div class="head-actions"><span class="count-pill"><b>${enabled.size}</b><span>已启用</span></span><button class="icon-button" data-action="reset-plan" title="恢复每日默认任务" ${state.isRunning || state.configError ? "disabled" : ""}>↺</button></div>
      </div>
      <div class="task-tools"><label class="field-label" for="add-task">添加现有任务</label><div class="add-row"><select id="add-task" ${available.length && !state.isRunning && !state.configError ? "" : "disabled"}><option value="">${available.length ? "选择一个已移除任务" : "全部任务已在计划中"}</option>${groupTasksByPhase(available).map((group) => `<optgroup label="${escapeHtml(group.phase)}">${group.tasks.map((task) => `<option value="${escapeHtml(task.id)}">${escapeHtml(task.name)}</option>`).join("")}</optgroup>`).join("")}</select><button class="button button-secondary" data-action="add-task" ${available.length && !state.isRunning && !state.configError ? "" : "disabled"}>添加</button></div></div>
      <div class="phase-filters" aria-label="按执行阶段筛选任务">${phaseFilters}</div>
      <div class="tasks-scroll">${rows || `<div class="empty-state">worker 尚未返回每日任务目录。</div>`}</div>
      <div class="planner-foot"><span class="muted">顺序跟随业务目录 · ${enabledTasks().length} 个任务启用</span><label class="switch-label"><input type="checkbox" data-setting="dry_run" ${state.config.dry_run ? "checked" : ""} ${state.isRunning || state.configError ? "disabled" : ""}><span class="switch-track"></span><span>模拟运行</span></label></div>
    </section>
    <aside class="plan-aside">
      <section class="panel operation-panel">
        <div class="operation-title"><div><div class="eyebrow">RUN CONTROL</div><h3>执行控制</h3></div><span class="state-lamp ${statusTone()}"></span></div>
        <div class="operation-status"><span>${statusLabel()}</span>${state.isRunning ? `<strong>${escapeHtml(currentTaskName())}</strong>` : `<strong>${state.progress?.finished_at ? `最近运行 ${escapeHtml(shortTime(state.progress.finished_at))}` : "等待启动"}</strong>`}</div>
        ${renderRunProgress()}<button class="button button-primary run-button" data-action="run-daily" ${!enabledTasks().length || state.isRunning || state.configError ? "disabled" : ""}><span class="button-glyph">${state.isRunning ? "●" : "▶"}</span>${state.isRunning ? "正在运行" : state.config.dry_run ? "开始模拟" : "开始执行"}</button>
        <button class="button button-stop run-button" data-action="stop" ${state.isRunning ? "" : "disabled"}>■　停止（⌃⌥⌘K）</button>
        <p class="fine-print">脚本结束表示操作流程已执行，不代表奖励已由游戏确认领取。</p>
      </section>
      <section class="panel start-panel">
        <div class="eyebrow">ENTRY POINT</div><h3>从哪里开始</h3><p>只执行所选起点及其后续启用任务。</p>
        <label class="field-label" for="start-task">起始任务</label><select id="start-task" ${enabledTasks().length && !state.isRunning && !state.configError ? "" : "disabled"}>${groupTasksByPhase(enabledTasks()).map((group) => `<optgroup label="${escapeHtml(group.phase)}">${group.tasks.map((task) => `<option value="${escapeHtml(task.id)}" ${task.id === selected?.id ? "selected" : ""}>${escapeHtml(task.name)}</option>`).join("")}</optgroup>`).join("")}</select>
        <div class="entry-card"><span class="entry-icon">⌖</span><div><span class="field-label">需要的游戏页面</span><strong>${escapeHtml(selected?.entry_page || "先添加并启用一个任务")}</strong></div></div>
        <div class="route-summary"><div><span>本次预计步骤</span><strong>${runCount}<small> 项</small></strong></div><div><span>默认流程</span><strong>${tasks().length}<small> 项</small></strong></div></div>
        <ol class="mini-route">${sourceAfterStart.slice(0, 5).map((task, index) => `<li><span class="route-dot ${index === 0 ? "route-dot-active" : ""}"></span><span>${escapeHtml(task.name)}</span><small>${index === 0 ? "开始" : `+${index}`}</small></li>`).join("")}${sourceAfterStart.length > 5 ? `<li class="route-more">还有 ${sourceAfterStart.length - 5} 个后续任务</li>` : ""}</ol>
      </section>
    </aside>
  </div>`;
}

function currentTaskName() {
  const taskId = state.progress?.current_task_id;
  return tasks().find((task) => task.id === taskId)?.name ?? "正在准备任务…";
}

function renderRunProgress() {
  if (!state.runPlanCount) return "";
  const completed = Math.min(state.completedTaskIds.length, state.runPlanCount);
  const percent = Math.round((completed / state.runPlanCount) * 100);
  return `<div class="execution-progress"><div class="progress-track"><span style="width:${percent}%"></span></div><div class="progress-meta"><span>${state.isRunning ? "本次进度" : "最近进度"}</span><strong>${completed} / ${state.runPlanCount} 项</strong></div></div>`;
}

function shortTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit" }).format(date);
}

function fieldControl(arg, current, commandId, { emptyChoiceLabel = "默认入口" } = {}) {
  const label = escapeHtml(arg.label || ARG_LABELS[arg.name] || arg.name);
  const value = current ?? arg.default ?? "";
  const required = arg.required ? "required" : "";
  const attrs = `data-arg="${escapeHtml(arg.name)}" ${required} ${state.isRunning || state.configError ? "disabled" : ""}`;
  if (Array.isArray(arg.choices) && arg.choices.length) {
    const defaultChoice = !arg.required && value === "" ? `<option value="" selected>${escapeHtml(emptyChoiceLabel)}</option>` : "";
    return `<label class="command-field"><span>${label}${arg.required ? " · 必填" : ""}</span><select ${attrs}>${defaultChoice}${arg.choices.map((choice) => `<option value="${escapeHtml(choice)}" ${String(choice) === String(value) ? "selected" : ""}>${escapeHtml(choiceLabel(choice, commandId, arg.name))}</option>`).join("")}</select></label>`;
  }
  if (["bool", "boolean", "flag"].includes(arg.type)) {
    return `<label class="command-bool"><input type="checkbox" ${attrs} ${value === true || value === "true" || value === 1 ? "checked" : ""}><span class="switch-track"></span><span>${label}</span></label>`;
  }
  const numeric = ["int", "integer", "float", "number"].includes(arg.type) || typeof value === "number";
  const type = numeric ? "number" : "text";
  const step = ["int", "integer"].includes(arg.type) ? "1" : "any";
  const min = arg.name.endsWith("task_claims") ? 'min="0"' : "";
  const max = arg.name === "mechanical_shock_task_claims" ? 'max="3"' : "";
  return `<label class="command-field"><span>${label}${arg.required ? " · 必填" : ""}</span><input type="${type}" step="${step}" ${min} ${max} value="${escapeHtml(value)}" placeholder="${escapeHtml(arg.placeholder || "")}" ${attrs}></label>`;
}

function choiceLabel(choice, commandId, argumentName) {
  if (argumentName === "backend") return BACKEND_NAMES[choice] || choice;
  if (argumentName === "armed_skip_animation_state") return ({ checked: "已勾选", unchecked: "未勾选" })[choice] || choice;
  if (argumentName === "armed_free_draw_state") return ({ available: "可领取", claimed: "已领取" })[choice] || choice;
  if (argumentName === "mechanical_shock_skip_animation_state") return ({ checked: "已勾选", unchecked: "未勾选" })[choice] || choice;
  if (argumentName === "mechanical_shock_mech_fight_claim_state") return ({ available: "可领取", claimed: "已领取" })[choice] || choice;
  if (["pass_free_claim_state", "free_claim_state"].includes(argumentName)) return ({ available: "可领取", claimed: "已领取" })[choice] || choice;
  if (["pass_work_plan_sign_state", "work_plan_sign_state"].includes(argumentName)) return ({ available: "可签到", claimed: "已签到" })[choice] || choice;
  if (argumentName === "mimic_skip_animation_state") return ({ checked: "已勾选", unchecked: "未勾选" })[choice] || choice;
  if (argumentName === "mimic_free_draw_state") return ({ available: "可领取", claimed: "已领取" })[choice] || choice;
  if (argumentName === "mimic_one_click_claim_state") return ({ available: "可领取", claimed: "已领取" })[choice] || choice;
  if (argumentName === "from_task") {
    if (commandId === "daily-rewards") return tasks().find((task) => task.id === choice)?.name || TASK_CHOICE_NAMES[choice] || choice;
    return TASK_CHOICE_NAMES[choice] || choice;
  }
  return choice;
}

function commandDescription(command) {
  const description = command.description || "";
  if (/^usage:/i.test(description.trim())) return `使用现有「${command.name}」操作，可编辑的参数已列在下方。`;
  return description || "使用现有本机操作执行本次任务。";
}

function commandEntryPage(command) {
  const fromTask = (command.args ?? []).find((arg) => arg.name === "from_task");
  if (!fromTask || !command.entry_pages) return command.entry_page || "由脚本检查";
  const selected = getCommandArgumentValue(state.config, command, fromTask);
  return command.entry_pages[String(selected)] || command.entry_page || "由脚本检查";
}

function renderCommand() {
  const command = chosenCommand();
  if (!command) return `<section class="panel empty-state">worker 尚未返回命令目录。</section>`;
  const entryPage = commandEntryPage(command);
  const args = command.args ?? [];
  return `<div class="command-layout"><section class="panel command-panel">
      <div class="eyebrow">COMMAND / SINGLE OPERATION</div><h2>单条命令</h2><p class="panel-subtitle">选择已有操作，参数控件由命令目录生成。</p>
      <label class="command-field command-select"><span>操作命令</span><select id="command-select" ${state.configError || state.isRunning ? "disabled" : ""}>${groupCommandsByCategory(commands()).map((group) => `<optgroup label="${escapeHtml(group.category)}">${group.commands.map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === command.id ? "selected" : ""}>${escapeHtml(item.name)}</option>`).join("")}</optgroup>`).join("")}</select></label>
      <div class="command-description"><span class="description-mark">i</span><div><strong>${escapeHtml(command.name)}</strong><p>${escapeHtml(commandDescription(command))}</p><span>入口页面：${escapeHtml(entryPage)}</span></div></div>
      <div class="argument-grid">${args.map((arg) => fieldControl(arg, getCommandArgumentValue(state.config, command, arg), command.id)).join("") || `<div class="muted">此命令不需要额外参数。</div>`}</div>
      <div class="command-foot"><label class="switch-label"><input type="checkbox" data-setting="dry_run" ${state.config.dry_run ? "checked" : ""} ${state.isRunning || state.configError ? "disabled" : ""}><span class="switch-track"></span><span>模拟运行</span></label><span class="muted">参数以独立数组传递</span></div>
    </section><aside class="plan-aside"><section class="panel operation-panel command-operation">
      <div class="operation-title"><div><div class="eyebrow">READY CHECK</div><h3>运行摘要</h3></div><span class="state-lamp ${statusTone()}"></span></div>
      <div class="summary-line"><span>当前命令</span><strong>${escapeHtml(command.name)}</strong></div><div class="summary-line"><span>需要页面</span><strong>${escapeHtml(entryPage)}</strong></div><div class="summary-line"><span>运行方式</span><strong>${state.config.dry_run ? "模拟，不发送输入" : "实时输入"}</strong></div>
      ${renderRunProgress()}<button class="button button-primary run-button" data-action="run-command" ${state.isRunning || state.configError ? "disabled" : ""}>▶　${state.config.dry_run ? "模拟运行" : "执行命令"}</button><button class="button button-stop run-button" data-action="stop" ${state.isRunning ? "" : "disabled"}>■　停止（⌃⌥⌘K）</button><p class="fine-print">脚本会检查游戏窗口与输入条件；执行前请确认入口页面、可用次数与资源条件。</p>
    </section></aside></div>`;
}

function renderLogs() {
  const entries = state.logs.slice(-160).reverse();
  return `<section class="log-dock"><div class="log-header"><div><span class="log-led ${state.isRunning ? "log-led-live" : ""}"></span><strong>实时日志</strong><span class="log-count">${state.logs.length}</span></div><button class="text-button" data-action="clear-view-logs">清除视图</button></div><div class="log-list" id="log-list">${entries.length ? entries.map((entry) => `<div class="log-row log-${escapeHtml(entry.type || "log")}"><time>${escapeHtml(logTime(entry))}</time>${entry.task_id ? `<span class="log-tag">${escapeHtml(entry.task_name || entry.task_id)}</span>` : ""}<span class="log-message">${escapeHtml(entry.message || entry.status || "")}</span></div>`).join("") : `<div class="logs-empty">日志将在启动后显示。模拟运行不会发送鼠标输入。</div>`}</div></section>`;
}

function logTime(entry) {
  const raw = entry.time ?? entry.received_at;
  if (raw === undefined || raw === null) return "--:--:--";
  const date = new Date(raw);
  return Number.isNaN(date.valueOf()) ? String(raw) : date.toLocaleTimeString("zh-CN", { hour12: false });
}

function render() {
  if (!state.catalog) {
    byId("app").innerHTML = `<main class="loading-screen"><div class="brand-mark">ZF</div><p>正在载入本地任务目录…</p><span>${escapeHtml(state.error || "检查独立运行组件")}</span></main>`;
    return;
  }
  const active = state.selectedView === "daily";
  const unsupportedWindows = /win/i.test(navigator.platform || navigator.userAgent);
  byId("app").innerHTML = `<div class="shell">
    <aside class="rail"><div class="brand-mark">ZF<span>✳</span></div><div class="rail-line"></div><button class="rail-item ${active ? "rail-active" : ""}" data-view="daily" title="每日任务"><span>▦</span><small>日常</small></button><button class="rail-item ${!active ? "rail-active" : ""}" data-view="command" title="单条命令"><span>⌘</span><small>命令</small></button><div class="rail-bottom"><span class="platform-dot"></span><small>LOCAL</small></div></aside>
    <main class="main-column"><header class="topbar"><div><div class="breadcrumb">工作台 <span>/</span> ${active ? "每日任务" : "单条命令"}</div><div class="top-title">向僵尸开炮 <span>·</span> 日常助手</div></div><div class="topbar-right"><span class="machine-badge"><i></i> ${unsupportedWindows ? "Windows · 实时执行未支持" : "macOS · 本机执行"}</span><button class="top-pin ${state.onTop ? "is-pinned" : ""}" data-action="toggle-top" title="窗口保持在游戏画面上方">${state.onTop ? "◆" : "◇"}<span>${state.onTop ? "已置顶" : "置顶窗口"}</span></button><div class="status-chip"><span class="state-lamp ${statusTone()}"></span>${statusLabel()}</div></div></header>
      <div class="content"><div class="content-heading"><div><span class="eyebrow">LOCAL AUTOMATION CONSOLE</span><h1>${active ? "每日任务" : "单条命令"}</h1></div><span class="date-stamp">CONTROL DECK <b>01</b></span></div>
      ${configNotice()}${state.error ? `<section class="notice notice-error"><div><strong>操作未完成</strong><p>${escapeHtml(state.error)}</p></div></section>` : ""}${interruptionNotice()}${unsupportedWindows ? `<section class="notice notice-warn"><div><strong>Windows 实时自动化尚未实现</strong><p>当前版本保留任务界面与模拟流程；不会尝试 macOS 输入接口。</p></div></section>` : ""}${renderPermissions()}<section class="notice notice-warn"><div><strong>执行前核对游戏内限制</strong><p>完整巡逻默认普通快速巡逻 3 次、广告快速巡逻 5 次；玩法商店会选择最大购买量，基地挑战会消耗可用次数。请先确认入口页面、剩余次数、资源和广告条件。</p></div></section>
      ${active ? renderDaily() : renderCommand()}${renderLogs()}</div>
    </main>
    <footer class="app-footer"><span>本地执行 · 进度保存在用户数据目录</span><span>紧急停止 <kbd>⌃</kbd><kbd>⌥</kbd><kbd>⌘</kbd><kbd>K</kbd></span><span>任务完成 ≠ 奖励已验证</span></footer>
  </div>`;
}

function appendLog(event) {
  const date = new Date();
  const task = tasks().find((item) => item.id === event.task_id);
  state.logs.push({ ...event, task_name: task?.name, time: date.toLocaleTimeString("zh-CN", { hour12: false }) });
  if (state.logs.length > 1000) state.logs.splice(0, state.logs.length - 1000);
}

async function saveConfig() {
  try {
    await invoke("save_config", { config: state.config });
    return true;
  } catch (error) {
    state.error = `配置保存失败：${error}`;
    appendLog({ type: "error", message: state.error });
    return false;
  }
}

function normalizeConfig(config, taskIds) {
  const allowed = new Set(taskIds);
  const source = Array.isArray(config.enabled_task_ids) ? config.enabled_task_ids : taskIds;
  const enabled = taskIds.filter((id) => source.includes(id) && allowed.has(id));
  const start = enabled.includes(config.daily_start_task_id) ? config.daily_start_task_id : enabled[0] ?? null;
  const migrated = migrateSharedCommandArgs(config, commands());
  return { ...migrated, enabled_task_ids: enabled, daily_start_task_id: start, command_args: migrated.command_args, dry_run: config.dry_run ?? true };
}

async function init() {
  try {
    await listen("worker-event", ({ payload }) => {
      if (payload.type !== "run_plan") appendLog(payload);
      if (payload.type === "run_started" || payload.type === "task_started") {
        state.isRunning = true;
        state.activeRunId = payload.run_id ?? state.activeRunId;
      }
      if (payload.type === "run_plan" && Number.isInteger(payload.task_count) && payload.task_count >= 0) {
        // Worker 已按起点和阶段编译出真实计划，进度总数以叶任务数为准。
        state.runPlanCount = payload.task_count;
      }
      if (payload.type === "task_started") {
        state.progress = { ...state.progress, status: "running", current_task_id: payload.task_id, last_task_status: "running", run_id: state.activeRunId };
      } else if (payload.type === "task_finished" && payload.task_id) {
        if (payload.status === "completed" || payload.status === "skipped") {
          if (!state.completedTaskIds.includes(payload.task_id)) state.completedTaskIds.push(payload.task_id);
          state.progress = { ...state.progress, current_task_id: null, last_finished_task_id: payload.task_id, last_task_status: "completed" };
        } else {
          state.progress = { ...state.progress, current_task_id: payload.task_id, last_task_status: payload.status };
        }
      } else if (payload.type === "run_finished") {
        state.progress = { ...state.progress, status: payload.status, finished_at: payload.received_at ?? Date.now(), run_id: payload.run_id ?? state.activeRunId };
        state.isRunning = false;
        state.stopRequested = false;
        state.activeRunId = null;
        state.pendingStopRequested = false;
        state.stopDispatchIssued = false;
        state.stopRetryUsed = false;
        state.startPhase = null;
      }
      render();
      scrollLogsToBottom();
    });
    await listen("stop-requested", () => {
      if (state.isRunning) {
        state.stopRequested = true;
        render();
      }
    });
    try {
      state.permissions = await invoke("check_permissions");
    } catch (error) {
      state.permissionError = `无法读取 macOS 权限状态：${error}`;
    }
    state.catalog = await invoke("get_catalog");
    state.selectedCommandId = state.catalog.commands?.[0]?.id ?? null;
    const taskIds = tasks().map((task) => task.id);
    const data = await invoke("load_app_state", { taskIds });
    const rawConfig = data.config ?? {};
    state.config = normalizeConfig(rawConfig, taskIds);
    if (commands().some((command) => command.id === state.config.last_command)) state.selectedCommandId = state.config.last_command;
    state.progress = data.progress ?? null;
    state.configError = data.config_error ?? null;
    state.logs = data.recent_logs ?? [];
    const sharedArgsChanged = JSON.stringify(rawConfig.command_args ?? {}) !== JSON.stringify(state.config.command_args ?? {});
    if (!state.configError && (!data.config_exists || !data.config || sharedArgsChanged)) await saveConfig();
    if (data.interrupted) state.progress = data.progress;
    if (state.progress?.status === "interrupted" && state.config.enabled_task_ids.includes(state.progress.current_task_id)) {
      state.config.daily_start_task_id = state.progress.current_task_id;
    }
    render();
  } catch (error) {
    state.error = String(error);
    render();
  }
}

async function handlePermissionAction(action) {
  state.permissionBusy = true;
  state.permissionError = null;
  render();
  try {
    state.permissions = await invoke(
      action === "check" ? "check_permissions" : "request_accessibility_permission",
    );
  } catch (error) {
    state.permissionError = String(error);
  } finally {
    state.permissionBusy = false;
    render();
  }
}

function scrollLogsToBottom() {
  const element = byId("log-list");
  if (element) element.scrollTop = 0;
}

function collectCommandArgs(command, allowedNames = null) {
  const args = [];
  for (const meta of command.args ?? []) {
    if (allowedNames && !allowedNames.has(meta.name)) continue;
    const rawValue = getCommandArgumentValue(state.config, command, meta);
    if (rawValue === undefined || rawValue === null || rawValue === "") {
      if (meta.required) throw new Error(`请填写「${meta.label || meta.name}」`);
      continue;
    }
    const isBoolean = ["bool", "boolean", "flag"].includes(meta.type);
    if (isBoolean) {
      const on = rawValue === true || rawValue === "true" || rawValue === 1;
      if (on) args.push(meta.flag ?? meta.name);
      else {
        const falseFlag = meta.false_flag || meta.negative_flag || (meta.boolean_optional && meta.flag ? `--no-${meta.flag.replace(/^--/, "")}` : "");
        if (falseFlag) args.push(falseFlag);
      }
    } else if (meta.flag) {
      args.push(meta.flag, String(rawValue));
    } else {
      args.push(String(rawValue));
    }
  }
  return args;
}

async function beginRun(mode) {
  try {
    if (state.configError) throw new Error("配置文件损坏，请先恢复默认配置。");
    if (state.isRunning) return;
    state.error = null;
    const command = mode === "command" ? chosenCommand() : commands().find((item) => item.id === "daily-rewards") ?? null;
    const sharedPhaseRun = mode === "daily" || command?.id === "daily-rewards";
    const phaseTasks = mode === "daily" ? enabledTasks() : tasks();
    const commandArgs = command
      ? mode === "daily"
        ? collectCommandArgs(command, new Set(["fit"]))
        : collectCommandArgs(command)
      : [];
    const request = {
      mode,
      task_ids: [...state.config.enabled_task_ids],
      from_task: mode === "daily" ? selectedStartTask()?.id ?? null : null,
      command: mode === "command" ? command?.id ?? "" : "",
      args: commandArgs,
      // 按阶段传递共享参数快照，使 worker 使用单条命令当前保存的真实值。
      phase_args: sharedPhaseRun ? buildDailyPhaseArgs(phaseTasks, commands(), state.config) : {},
      dry_run: Boolean(state.config.dry_run),
    };
    if (mode === "command" && command) state.config.last_command = command.id;
    state.isRunning = true;
    state.stopRequested = false;
    state.pendingStopRequested = false;
    state.stopDispatchIssued = false;
    state.stopRetryUsed = false;
    state.startPhase = "saving";
    state.activeRunId = "pending";
    state.completedTaskIds = [];
    state.runPlanCount = mode === "daily"
      ? Math.max(0, enabledTasks().length - enabledTasks().findIndex((task) => task.id === request.from_task))
      : command?.id === "daily-rewards" ? tasks().length : 1;
    state.progress = { status: "running", current_task_id: mode === "daily" ? request.from_task : null, run_id: null, started_at: Date.now() };
    render();
    if (!(await saveConfig())) {
      state.isRunning = false;
      state.activeRunId = null;
      state.stopRequested = false;
      state.pendingStopRequested = false;
      state.stopDispatchIssued = false;
      state.startPhase = null;
      state.progress = { ...state.progress, status: "failed", finished_at: Date.now() };
      render();
      return;
    }
    if (state.pendingStopRequested) {
      state.isRunning = false;
      state.stopRequested = false;
      state.pendingStopRequested = false;
      state.activeRunId = null;
      state.startPhase = null;
      state.progress = { ...state.progress, status: "stopped", finished_at: Date.now() };
      appendLog({ type: "log", message: "启动前已取消；没有启动任务执行组件。" });
      render();
      return;
    }
    state.startPhase = "starting";
    const startPromise = invoke("start_run", { request });
    // 启动调用进行中也可以立刻把停止请求交给 Rust 侧的 pending-stop 闩锁。
    if (state.pendingStopRequested) void dispatchStopRun();
    const response = await startPromise;
    state.startPhase = null;
    if (state.isRunning && state.activeRunId === "pending") state.activeRunId = response.run_id;
    if (state.isRunning && state.progress?.run_id == null) {
      state.progress = { ...state.progress, run_id: response.run_id, started_at: response.started_at };
    }
    if (state.isRunning && state.pendingStopRequested && !state.stopDispatchIssued) void dispatchStopRun();
    if (state.isRunning) appendLog({ type: "log", message: request.dry_run ? "模拟流程已启动，不会发送鼠标输入。" : "实时执行已启动。" });
    render();
  } catch (error) {
    if (state.activeRunId === "pending") {
      state.isRunning = false;
      state.activeRunId = null;
      state.stopRequested = false;
      state.pendingStopRequested = false;
      state.stopDispatchIssued = false;
      state.startPhase = null;
      state.progress = { ...state.progress, status: "failed", finished_at: Date.now() };
    }
    state.error = String(error);
    appendLog({ type: "error", message: state.error });
    render();
  }
}

async function stopRun() {
  if (!state.isRunning || state.stopRequested) return;
  state.stopRequested = true;
  const waitingForLaunch = state.activeRunId === "pending" || state.startPhase !== null;
  if (waitingForLaunch) {
    state.pendingStopRequested = true;
    if (state.startPhase === "starting") void dispatchStopRun();
  }
  appendLog({ type: "log", message: "已请求停止；正在等待当前输入完成并结束 sidecar。" });
  render();
  if (waitingForLaunch) return;
  await dispatchStopRun();
}

async function dispatchStopRun() {
  if (state.stopDispatchIssued) return;
  state.stopDispatchIssued = true;
  try {
    const accepted = await invoke("stop_run");
    if (!accepted) {
      state.stopDispatchIssued = false;
      if (state.pendingStopRequested && state.startPhase === "starting") return;
      if (state.pendingStopRequested && state.isRunning && !state.stopRetryUsed) {
        state.stopRetryUsed = true;
        queueMicrotask(() => void dispatchStopRun());
        return;
      }
      state.stopRequested = false;
      appendLog({ type: "log", message: "停止未被任务接受；任务仍在运行时可再次点击停止。" });
      render();
      return;
    }
    render();
  } catch (error) {
    state.stopDispatchIssued = false;
    state.stopRequested = false;
    appendLog({ type: "error", message: `停止请求失败：${error}` });
    render();
  }
}

async function persistConfig() {
  await saveConfig();
  render();
}

document.addEventListener("click", async (event) => {
  const view = event.target.closest("[data-view]");
  if (view) {
    state.selectedView = view.dataset.view;
    render();
    return;
  }
  const phaseFilter = event.target.closest("[data-phase-filter]");
  if (phaseFilter) {
    state.selectedTaskPhase = phaseFilter.dataset.phaseFilter;
    render();
    return;
  }
  const action = event.target.closest("[data-action]")?.dataset.action;
  if (!action) return;
  if (state.configError && !["restore-defaults", "stop", "check-permissions", "request-permissions"].includes(action)) return;
  if (action === "check-permissions") return handlePermissionAction("check");
  if (action === "request-permissions") return handlePermissionAction("request");
  if (action === "run-daily") return beginRun("daily");
  if (action === "run-command") return beginRun("command");
  if (action === "stop") return stopRun();
  if (action === "clear-view-logs") { state.logs = []; render(); return; }
  if (action === "phase-tasks") {
    if (state.isRunning) return;
    const button = event.target.closest("[data-phase-id]");
    const phaseId = button?.dataset.phaseId;
    const phaseTaskIds = tasks().filter((task) => task.phase === phaseId).map((task) => task.id);
    if (!phaseTaskIds.length) return;
    const selected = new Set(state.config.enabled_task_ids);
    if (button.dataset.phaseMode === "clear") phaseTaskIds.forEach((id) => selected.delete(id));
    else phaseTaskIds.forEach((id) => selected.add(id));
    state.config.enabled_task_ids = tasks().filter((task) => selected.has(task.id)).map((task) => task.id);
    if (!state.config.enabled_task_ids.includes(state.config.daily_start_task_id)) {
      state.config.daily_start_task_id = state.config.enabled_task_ids[0] ?? null;
    }
    await persistConfig();
    return;
  }
  if (action === "route-tasks") {
    if (state.isRunning) return;
    const button = event.target.closest("[data-task-ids]");
    const selected = new Set(state.config.enabled_task_ids);
    const ids = (button?.dataset.taskIds || "").split(",").filter(Boolean);
    if (button?.dataset.taskMode === "clear") ids.forEach((id) => selected.delete(id));
    else ids.forEach((id) => selected.add(id));
    state.config.enabled_task_ids = tasks().filter((task) => selected.has(task.id)).map((task) => task.id);
    if (!state.config.enabled_task_ids.includes(state.config.daily_start_task_id)) state.config.daily_start_task_id = state.config.enabled_task_ids[0] ?? null;
    await persistConfig();
    return;
  }
  if (action === "toggle-top") {
    state.onTop = !state.onTop;
    try { await invoke("set_always_on_top", { enabled: state.onTop }); } catch (error) { state.error = String(error); }
    render();
    return;
  }
  if (action === "add-task") {
    const select = byId("add-task");
    if (!select?.value || state.isRunning) return;
    const id = select.value;
    state.config.enabled_task_ids = tasks().filter((task) => state.config.enabled_task_ids.includes(task.id) || task.id === id).map((task) => task.id);
    if (!state.config.daily_start_task_id) state.config.daily_start_task_id = id;
    await persistConfig();
    return;
  }
  if (action === "reset-plan") {
    if (state.isRunning) return;
    state.config.enabled_task_ids = tasks().map((task) => task.id);
    state.config.daily_start_task_id = tasks()[0]?.id ?? null;
    await persistConfig();
    return;
  }
  if (action === "resume-from-last") {
    const taskId = event.target.closest("[data-task-id]")?.dataset.taskId || state.progress?.current_task_id;
    if (taskId && state.config.enabled_task_ids.includes(taskId)) {
      state.config.daily_start_task_id = taskId;
      state.selectedView = "daily";
      await persistConfig();
    }
    return;
  }
  if (action === "restore-defaults") {
    try {
      const data = await invoke("restore_defaults", { taskIds: tasks().map((task) => task.id) });
      state.config = normalizeConfig(data.config, tasks().map((task) => task.id));
      state.configError = null;
      state.progress = data.progress ?? state.progress;
    } catch (error) { state.error = `恢复失败：${error}`; }
    render();
  }
});

document.addEventListener("change", async (event) => {
  const target = event.target;
  if (state.configError) return;
  if (target.matches("[data-task-toggle]")) {
    const id = target.dataset.taskToggle;
    const selected = new Set(state.config.enabled_task_ids);
    target.checked ? selected.add(id) : selected.delete(id);
    state.config.enabled_task_ids = tasks().filter((task) => selected.has(task.id)).map((task) => task.id);
    if (!state.config.enabled_task_ids.includes(state.config.daily_start_task_id)) state.config.daily_start_task_id = state.config.enabled_task_ids[0] ?? null;
    await persistConfig();
  } else if (target.id === "start-task") {
    state.config.daily_start_task_id = target.value || null;
    await persistConfig();
  } else if (target.id === "add-task") {
    // Keep the native selector editable; its value is consumed by the adjacent Add button.
  } else if (target.id === "command-select") {
    state.selectedCommandId = target.value;
    state.config.last_command = target.value;
    state.config.command_args ??= {};
    await persistConfig();
  } else if (target.matches("[data-setting]")) {
    state.config[target.dataset.setting] = target.checked;
    await persistConfig();
  } else if (target.matches("[data-arg]")) {
    const command = chosenCommand();
    state.config = setCommandArgumentValue(state.config, command, target.dataset.arg, target.type === "checkbox" ? target.checked : target.value);
    await persistConfig();
  }
});

window.addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.altKey && event.metaKey && event.code === "KeyK") {
    event.preventDefault();
    stopRun();
  }
});

await init();
