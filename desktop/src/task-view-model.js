export const PHASE_NAMES = {
  patrol: "巡逻收益",
  mechanical_shock: "机械震荡",
  battle_pass: "通行证",
  armed_descent: "武装降临",
  mimic_card_library: "拟态牌库",
  calendar: "日历礼包",
  welfare: "福利奖励",
  mail: "邮件奖励",
  legion: "军团事务",
  journey: "征途任务",
  base: "基地挑战",
  shop: "商城采购",
};

export const PHASE_ORDER = Object.keys(PHASE_NAMES);

export const DAILY_PHASE_COMMANDS = {
  patrol: "patrol-full-from-home",
  mechanical_shock: "mechanical-shock",
  battle_pass: "battle-pass-daily",
  armed_descent: "armed-descent",
  mimic_card_library: "mimic-card-library",
  calendar: "calendar-claim",
  welfare: "welfare-claim",
  mail: "mail-claim",
  legion: "legion-daily-rewards",
  journey: "journey-daily-rewards",
  base: "base-training-hall",
  shop: "shop-training-hall",
};

export const COMMAND_CATEGORY_NAMES = {
  daily: "每日综合",
  patrol: "巡逻",
  rewards: "奖励领取",
  legion: "军团",
  journey: "征途",
  base: "基地挑战",
  shop: "商城采购",
  other: "其他命令",
};

export function groupTasksByPhase(source) {
  const groups = [];
  for (const task of source) {
    let group = groups.at(-1);
    if (!group || group.phaseId !== task.phase) {
      group = {
        phaseId: task.phase,
        phase: PHASE_NAMES[task.phase] || task.phase || "日常",
        tasks: [],
      };
      groups.push(group);
    }
    group.tasks.push(task);
  }
  return groups;
}

export function groupTasksByRoute(source) {
  const tabs = [];
  for (const task of source) {
    let tab = tabs.at(-1);
    if (!tab || tab.tab !== task.tab) {
      tab = { tabId: task.tab, tab: task.tab || "游戏", modules: [] };
      tabs.push(tab);
    }
    let module = tab.modules.at(-1);
    if (!module || module.module !== task.module) {
      module = { module: task.module || task.phase || "日常", tasks: [] };
      tab.modules.push(module);
    }
    module.tasks.push(task);
  }
  return tabs;
}

export function migrateSharedCommandArgs(config, commands) {
  const migrated = { ...config, command_args: Object.fromEntries(Object.entries(config.command_args ?? {}).map(([id, values]) => [id, { ...values }])) };
  const shared = { ...(migrated.command_args.$shared ?? {}) };
  const candidates = new Map();
  for (const command of commands) {
    const values = migrated.command_args[command.id] ?? {};
    for (const arg of command.args ?? []) {
      if (!arg.shared_key || !Object.hasOwn(values, arg.name)) continue;
      if (!candidates.has(arg.shared_key)) candidates.set(arg.shared_key, []);
      candidates.get(arg.shared_key).push({ commandId: command.id, value: values[arg.name] });
    }
  }
  for (const [key, values] of candidates) {
    if (!Object.hasOwn(shared, key)) {
      const preferred = values.find((entry) => entry.commandId === config.last_command);
      shared[key] = preferred ? preferred.value : values[0].value;
    }
  }
  for (const command of commands) {
    const values = migrated.command_args[command.id];
    if (!values) continue;
    for (const arg of command.args ?? []) if (arg.shared_key) delete values[arg.name];
  }
  migrated.command_args.$shared = shared;
  return migrated;
}

function argumentValue(config, command, arg) {
  const shared = config.command_args?.$shared ?? {};
  const commandValues = config.command_args?.[command.id] ?? {};
  const hasSavedValue = arg.shared_key && Object.hasOwn(shared, arg.shared_key)
    ? true
    : Object.hasOwn(commandValues, arg.name);
  if (!hasSavedValue) return arg.default;
  const savedValue = arg.shared_key && Object.hasOwn(shared, arg.shared_key)
    ? shared[arg.shared_key]
    : commandValues[arg.name];
  const isStartArgument = arg.name === "from_task" || arg.name === "from_step";
  if (!isStartArgument && Object.hasOwn(arg, "default") && (savedValue === null || savedValue === undefined || savedValue === "")) {
    return arg.default;
  }
  return savedValue;
}

export function getCommandArgumentValue(config, command, arg) {
  return argumentValue(config, command, arg);
}

function commandArgumentTokens(command, config, excluded = new Set()) {
  const tokens = [];
  for (const arg of command.args ?? []) {
    if (excluded.has(arg.name)) continue;
    const value = argumentValue(config, command, arg);
    if (value === undefined || value === null || value === "") continue;
    const boolean = ["bool", "boolean", "flag"].includes(arg.type);
    if (boolean) {
      const enabled = value === true || value === "true" || value === 1;
      if (enabled) tokens.push(arg.flag ?? arg.name);
      else if (arg.false_flag || arg.negative_flag) tokens.push(arg.false_flag || arg.negative_flag);
    } else if (arg.flag) tokens.push(arg.flag, String(value));
    else tokens.push(String(value));
  }
  return tokens;
}

export function setCommandArgumentValue(config, command, argumentName, value) {
  const next = { ...config, command_args: { ...(config.command_args ?? {}) } };
  if (command.args?.find((arg) => arg.name === argumentName)?.shared_key) {
    const key = command.args.find((arg) => arg.name === argumentName).shared_key;
    next.command_args.$shared = { ...(next.command_args.$shared ?? {}), [key]: value };
  } else {
    next.command_args[command.id] = { ...(next.command_args[command.id] ?? {}), [argumentName]: value };
  }
  return next;
}

export function buildDailyPhaseArgs(dailyTasks, commands, config) {
  const commandById = new Map(commands.map((command) => [command.id, command]));
  const phases = [...new Set(dailyTasks.map((task) => task.phase))];
  return Object.fromEntries(phases.map((phase) => {
    const command = commandById.get(DAILY_PHASE_COMMANDS[phase]);
    return [phase, command ? commandArgumentTokens(command, config, new Set(["from_task"])) : []];
  }));
}

export function shouldRenderPermissionNotice(permissions, error = null) {
  error = error ?? permissions?.error ?? null;
  if (permissions?.platform !== "macos" && !error) return false;
  return !(permissions?.accessibility === "granted" && permissions?.automation === "granted" && !error);
}

export function shouldExpandPermissionNotice(permissions, error = null) {
  error = error ?? permissions?.error ?? null;
  return !(permissions?.accessibility === "granted" && permissions?.automation === "not_checked" && !error);
}

export function groupCommandsByCategory(source) {
  const groups = new Map();
  for (const command of source) {
    const categoryId = COMMAND_CATEGORY_NAMES[command.category] ? command.category : "other";
    let group = groups.get(categoryId);
    if (!group) {
      group = { categoryId, category: COMMAND_CATEGORY_NAMES[categoryId], commands: [] };
      groups.set(categoryId, group);
    }
    group.commands.push(command);
  }
  return [...groups.values()];
}
