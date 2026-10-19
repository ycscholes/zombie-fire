mod lifecycle;
mod permissions;

use lifecycle::{
    apply_task_finished, apply_task_started, recover_progress, resolve_worker_status,
    PersistedProgress, RunGate, RunRequest, RunSnapshot, WorkerStopState,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    collections::HashMap,
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
    sync::{
        atomic::{AtomicBool, AtomicU64, Ordering},
        Mutex,
    },
    time::{Duration, SystemTime, UNIX_EPOCH},
};
use tauri::{path::BaseDirectory, AppHandle, Emitter, Manager, RunEvent, State, WebviewWindow};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};

const WORKER_SIDECAR: &str = "zombie-fire-worker";
const CGCLICK_RESOURCE: &str = "resources/bin/zombie_cgclick";
const STOP_CONTROL_LINE: &[u8] = b"{\"type\":\"stop\"}\n";
const STOP_GRACE: Duration = Duration::from_secs(6);
const LOG_ROTATE_BYTES: u64 = 5 * 1024 * 1024;
static RUN_COUNTER: AtomicU64 = AtomicU64::new(0);

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(default)]
struct AppConfig {
    enabled_task_ids: Vec<String>,
    #[serde(default)]
    pass_daily_migration_applied: bool,
    daily_start_task_id: Option<String>,
    last_command: Option<String>,
    command_args: HashMap<String, Value>,
    #[serde(default = "default_dry_run")]
    dry_run: bool,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            enabled_task_ids: Vec::new(),
            pass_daily_migration_applied: false,
            daily_start_task_id: None,
            last_command: None,
            command_args: HashMap::new(),
            dry_run: true,
        }
    }
}

fn default_dry_run() -> bool {
    true
}

impl AppConfig {
    fn for_catalog(task_ids: &[String]) -> Self {
        Self {
            enabled_task_ids: task_ids.to_vec(),
            pass_daily_migration_applied: true,
            daily_start_task_id: task_ids.first().cloned(),
            ..Self::default()
        }
    }

    fn reconcile(mut self, task_ids: &[String]) -> Self {
        let mut enabled = self
            .enabled_task_ids
            .iter()
            .cloned()
            .collect::<std::collections::HashSet<_>>();
        if !self.pass_daily_migration_applied
            && task_ids.iter().any(|task_id| task_id == "pass.daily")
        {
            // 旧配置首次遇到通行证任务时启用它；目录顺序使其排在最后一个已启用巡逻任务后，无巡逻时居首。
            enabled.insert("pass.daily".to_string());
            self.pass_daily_migration_applied = true;
        }
        self.enabled_task_ids = task_ids
            .iter()
            .filter(|task_id| enabled.contains(*task_id))
            .cloned()
            .collect();
        if !self
            .daily_start_task_id
            .as_ref()
            .is_some_and(|task_id| self.enabled_task_ids.contains(task_id))
        {
            self.daily_start_task_id = self.enabled_task_ids.first().cloned();
        }
        self
    }
}

struct DataPaths {
    config: PathBuf,
    progress: PathBuf,
    logs: PathBuf,
}

impl DataPaths {
    fn new(app_data_dir: PathBuf) -> Self {
        Self {
            config: app_data_dir.join("config.json"),
            progress: app_data_dir.join("progress.json"),
            logs: app_data_dir.join("runs.jsonl"),
        }
    }
}

struct ProcessControl {
    run_id: String,
    child: Option<CommandChild>,
    stop: WorkerStopState,
}

struct AppState {
    paths: DataPaths,
    gate: Mutex<RunGate>,
    process: Mutex<Option<ProcessControl>>,
    pending_stop: AtomicBool,
    shutdown_started: AtomicBool,
    config_error: Mutex<Option<String>>,
}

impl AppState {
    fn initialize(app_data_dir: PathBuf) -> Result<Self, String> {
        fs::create_dir_all(&app_data_dir)
            .map_err(|error| format!("无法创建应用数据目录：{error}"))?;
        let paths = DataPaths::new(app_data_dir);
        if let Some(saved) = read_json::<PersistedProgress>(&paths.progress)? {
            let recovered = recover_progress(saved.clone());
            if recovered != saved {
                write_json_atomic(&paths.progress, &recovered)?;
            }
        }
        Ok(Self {
            paths,
            gate: Mutex::new(RunGate::default()),
            process: Mutex::new(None),
            pending_stop: AtomicBool::new(false),
            shutdown_started: AtomicBool::new(false),
            config_error: Mutex::new(None),
        })
    }
}

#[derive(Serialize)]
struct LoadedState {
    config: AppConfig,
    config_exists: bool,
    config_error: Option<String>,
    progress: Option<PersistedProgress>,
    interrupted: bool,
    recent_logs: Vec<Value>,
}

#[derive(Serialize)]
struct StartResponse {
    run_id: String,
    started_at: u64,
}

#[derive(Serialize)]
struct RestoredState {
    config: AppConfig,
    progress: Option<PersistedProgress>,
}

fn unix_millis() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}

fn new_run_id() -> String {
    format!(
        "{}-{}-{}",
        unix_millis(),
        std::process::id(),
        RUN_COUNTER.fetch_add(1, Ordering::Relaxed)
    )
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<Option<T>, String> {
    if !path.exists() {
        return Ok(None);
    }
    let mut file =
        File::open(path).map_err(|error| format!("无法读取 {}：{error}", path.display()))?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)
        .map_err(|error| format!("无法读取 {}：{error}", path.display()))?;
    serde_json::from_slice(&bytes)
        .map(Some)
        .map_err(|error| format!("{} 不是有效 JSON：{error}", path.display()))
}

fn write_json_atomic<T: Serialize>(path: &Path, value: &T) -> Result<(), String> {
    let parent = path
        .parent()
        .ok_or_else(|| "应用数据路径没有父目录".to_string())?;
    fs::create_dir_all(parent).map_err(|error| format!("无法准备应用数据目录：{error}"))?;
    let temp = path.with_extension(format!(
        "tmp-{}-{}",
        std::process::id(),
        RUN_COUNTER.fetch_add(1, Ordering::Relaxed)
    ));
    let bytes =
        serde_json::to_vec_pretty(value).map_err(|error| format!("无法编码 JSON：{error}"))?;
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temp)
        .map_err(|error| format!("无法写入临时文件：{error}"))?;
    if let Err(error) = file.write_all(&bytes).and_then(|_| file.sync_all()) {
        let _ = fs::remove_file(&temp);
        return Err(format!("无法保存临时文件：{error}"));
    }
    drop(file);
    fs::rename(&temp, path).map_err(|error| {
        let _ = fs::remove_file(&temp);
        format!("无法原子替换 {}：{error}", path.display())
    })
}

fn read_recent_logs(path: &Path) -> Vec<Value> {
    let Ok(content) = fs::read_to_string(path) else {
        return Vec::new();
    };
    content
        .lines()
        .rev()
        .take(200)
        .filter_map(|line| serde_json::from_str(line).ok())
        .collect::<Vec<_>>()
        .into_iter()
        .rev()
        .collect()
}

fn append_event_log(path: &Path, event: &Value) {
    if let Ok(metadata) = fs::metadata(path) {
        if metadata.len() >= LOG_ROTATE_BYTES {
            let rotated = path.with_extension("jsonl.1");
            let _ = fs::remove_file(&rotated);
            let _ = fs::rename(path, rotated);
        }
    }
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(path) {
        let mut event = event.clone();
        if let Some(object) = event.as_object_mut() {
            object.insert("received_at".to_string(), json!(unix_millis()));
        }
        if let Ok(line) = serde_json::to_vec(&event) {
            let _ = file.write_all(&line);
            let _ = file.write_all(b"\n");
        }
    }
}

fn progress_for_run(run_id: &str, request: &RunRequest, started_at: u64) -> PersistedProgress {
    PersistedProgress {
        status: "running".to_string(),
        current_task_id: (request.mode == "daily")
            .then(|| request.from_task.clone())
            .flatten(),
        last_finished_task_id: None,
        last_task_status: None,
        run_id: Some(run_id.to_string()),
        started_at: Some(started_at),
        finished_at: None,
    }
}

fn save_progress(paths: &DataPaths, progress: &PersistedProgress) {
    let _ = write_json_atomic(&paths.progress, progress);
}

fn emit_event(app: &AppHandle, paths: &DataPaths, event: Value) {
    append_event_log(&paths.logs, &event);
    let _ = app.emit("worker-event", event);
}

#[tauri::command]
async fn get_catalog(app: AppHandle) -> Result<Value, String> {
    let command = app
        .shell()
        .sidecar(WORKER_SIDECAR)
        .map_err(|error| format!("桌面执行组件未安装：{error}"))?
        .args(["catalog"])
        .env("PYTHONUTF8", "1");
    let (mut receiver, _child) = command
        .spawn()
        .map_err(|error| format!("无法启动任务目录：{error}"))?;
    let mut stdout = Vec::new();
    let mut stderr = Vec::new();
    let mut exit_code = None;
    while let Some(event) = receiver.recv().await {
        match event {
            CommandEvent::Stdout(bytes) => stdout.extend(bytes),
            CommandEvent::Stderr(bytes) => stderr.extend(bytes),
            CommandEvent::Terminated(status) => {
                exit_code = status.code;
                break;
            }
            CommandEvent::Error(error) => stderr.extend(error.as_bytes()),
            _ => {}
        }
    }
    if exit_code != Some(0) {
        let detail = String::from_utf8_lossy(&stderr).trim().to_string();
        return Err(if detail.is_empty() {
            format!(
                "任务目录加载失败，执行组件退出码：{}",
                exit_code.unwrap_or(-1)
            )
        } else {
            format!("任务目录加载失败：{detail}")
        });
    }
    serde_json::from_slice(&stdout).map_err(|error| {
        format!(
            "任务目录格式无法识别：{error}。输出：{}",
            String::from_utf8_lossy(&stdout).trim()
        )
    })
}

#[tauri::command]
fn load_app_state(task_ids: Vec<String>, state: State<'_, AppState>) -> LoadedState {
    let config_path = &state.paths.config;
    let config_exists = config_path.exists();
    let mut error = None;
    let config = if !config_exists {
        AppConfig::for_catalog(&task_ids)
    } else {
        match read_json::<Value>(config_path) {
            Ok(Some(raw)) => {
                if raw.get("enabled_task_ids").is_none() {
                    error = Some("配置缺少 enabled_task_ids 字段".to_string());
                    AppConfig::for_catalog(&task_ids)
                } else {
                    serde_json::from_value::<AppConfig>(raw)
                        .map(|config| config.reconcile(&task_ids))
                        .unwrap_or_else(|parse_error| {
                            error = Some(parse_error.to_string());
                            AppConfig::for_catalog(&task_ids)
                        })
                }
            }
            Ok(None) => AppConfig::for_catalog(&task_ids),
            Err(parse_error) => {
                error = Some(parse_error);
                AppConfig::for_catalog(&task_ids)
            }
        }
    };
    if let Ok(mut shared_error) = state.config_error.lock() {
        *shared_error = error.clone();
    }
    let progress = read_json::<PersistedProgress>(&state.paths.progress)
        .ok()
        .flatten();
    let interrupted = progress
        .as_ref()
        .is_some_and(|item| item.status == "interrupted");
    LoadedState {
        config,
        config_exists,
        config_error: error,
        progress,
        interrupted,
        recent_logs: read_recent_logs(&state.paths.logs),
    }
}

#[tauri::command]
fn save_config(config: AppConfig, state: State<'_, AppState>) -> Result<(), String> {
    if state
        .config_error
        .lock()
        .map_err(|_| "配置状态不可用".to_string())?
        .is_some()
    {
        return Err("配置文件损坏，请先恢复默认配置；原文件将保留备份。".to_string());
    }
    write_json_atomic(&state.paths.config, &config)?;
    if let Ok(mut error) = state.config_error.lock() {
        *error = None;
    }
    Ok(())
}

#[tauri::command]
fn restore_defaults(
    task_ids: Vec<String>,
    state: State<'_, AppState>,
) -> Result<RestoredState, String> {
    if state.paths.config.exists() {
        let backup = state
            .paths
            .config
            .with_file_name(format!("config.corrupt-{}.json", unix_millis()));
        fs::copy(&state.paths.config, &backup)
            .map_err(|error| format!("无法备份损坏配置到 {}：{error}", backup.display()))?;
    }
    let config = AppConfig::for_catalog(&task_ids);
    write_json_atomic(&state.paths.config, &config)?;
    if let Ok(mut error) = state.config_error.lock() {
        *error = None;
    }
    let progress = read_json::<PersistedProgress>(&state.paths.progress)
        .ok()
        .flatten();
    Ok(RestoredState { config, progress })
}

#[tauri::command]
async fn start_run(
    app: AppHandle,
    state: State<'_, AppState>,
    request: RunRequest,
) -> Result<StartResponse, String> {
    if request.mode != "daily" && request.mode != "command" {
        return Err("只允许每日任务或已登记的单条命令".to_string());
    }
    if request.mode == "daily" && request.from_task.is_none() {
        return Err("请先选择一个启用的起始任务".to_string());
    }
    let request_bytes = serde_json::to_vec(&request).map_err(|error| error.to_string())?;
    #[cfg(target_os = "windows")]
    if !request.dry_run {
        return Err("Windows 实时输入尚未实现；当前只能运行模拟流程".to_string());
    }

    let run_id = new_run_id();
    let snapshot = RunSnapshot::capture(run_id.clone(), &request);
    state
        .gate
        .lock()
        .map_err(|_| "运行状态不可用".to_string())?
        .begin(snapshot)?;

    if !request.dry_run {
        // 先占用运行闩锁避免并发弹出多份授权请求，再做权限检查；失败时不写进度或启动 sidecar。
        let preflight =
            match tauri::async_runtime::spawn_blocking(permissions::live_preflight).await {
                Ok(result) => result,
                Err(error) => Err(format!("权限预检任务失败：{error}")),
            };
        if let Err(error) = preflight {
            finish_gate(&state, &run_id);
            return Err(error);
        }
    }

    let started_at = unix_millis();
    let mut progress = progress_for_run(&run_id, &request, started_at);
    if let Err(error) = write_json_atomic(&state.paths.progress, &progress) {
        finish_gate(&state, &run_id);
        return Err(error);
    }

    let mut sidecar = match app.shell().sidecar(WORKER_SIDECAR) {
        Ok(sidecar) => sidecar,
        Err(error) => {
            progress.status = "failed".to_string();
            progress.finished_at = Some(unix_millis());
            save_progress(&state.paths, &progress);
            finish_gate(&state, &run_id);
            return Err(format!("桌面执行组件未安装：{error}"));
        }
    };
    sidecar = sidecar
        .args(["run"])
        .env("PYTHONUTF8", "1")
        .env("PYTHONUNBUFFERED", "1")
        .set_process_group(true);
    if let Ok(helper) = app
        .path()
        .resolve(CGCLICK_RESOURCE, BaseDirectory::Resource)
    {
        sidecar = sidecar.env("ZOMBIE_CGCLICK_BIN", helper.to_string_lossy().as_ref());
    }
    let (receiver, child) = match sidecar.spawn() {
        Ok(spawned) => spawned,
        Err(error) => {
            progress.status = "failed".to_string();
            progress.finished_at = Some(unix_millis());
            save_progress(&state.paths, &progress);
            finish_gate(&state, &run_id);
            return Err(format!("无法启动任务执行组件：{error}"));
        }
    };

    {
        let mut active = state
            .process
            .lock()
            .map_err(|_| "任务进程状态不可用".to_string())?;
        if active.is_some() {
            drop(active);
            let _ = child.kill();
            finish_gate(&state, &run_id);
            return Err("已有任务进程尚未退出，请稍候".to_string());
        }
        *active = Some(ProcessControl {
            run_id: run_id.clone(),
            child: Some(child),
            stop: WorkerStopState::new(state.pending_stop.swap(false, Ordering::SeqCst)),
        });
    }

    let _ = app.emit(
        "worker-event",
        json!({"type":"run_started", "message":"执行计划已锁定并启动。", "run_id":run_id}),
    );
    let paths = state.paths.clone_for_monitor();
    let app_for_monitor = app.clone();
    let monitor_run_id = run_id.clone();
    tauri::async_runtime::spawn(async move {
        monitor_run(app_for_monitor, paths, receiver, monitor_run_id).await;
    });

    let write_result = (|| -> Result<bool, String> {
        let mut active = state
            .process
            .lock()
            .map_err(|_| "任务进程状态不可用".to_string())?;
        let process = active
            .as_mut()
            .filter(|process| process.run_id == run_id)
            .ok_or_else(|| "任务进程在启动时退出".to_string())?;
        if !process.stop.may_send_initial_request() {
            // 停止先于计划写入时，sidecar 仍只在等待首行；直接清理它，避免输入线程抢跑。
            process
                .child
                .take()
                .ok_or_else(|| "任务进程已停止".to_string())?
                .kill()
                .map_err(|error| format!("无法取消尚未启动的 sidecar：{error}"))?;
            return Ok(false);
        }
        process
            .child
            .as_mut()
            .ok_or_else(|| "任务进程已停止".to_string())?
            .write(&[request_bytes.as_slice(), b"\n"].concat())
            .map_err(|error| format!("无法向执行组件发送计划：{error}"))?;
        process.stop.mark_request_sent();
        Ok(true)
    })();

    if let Err(error) = write_result {
        let _ = app.emit(
            "worker-event",
            json!({"type":"error", "message":error, "run_id":run_id}),
        );
        let (request_sent, child) = {
            let state = app.state::<AppState>();
            let mut active = state.process.lock().ok();
            let process = active.as_mut().and_then(|active| active.as_mut());
            let Some(process) = process else {
                return Err(error);
            };
            if process.stop.request_sent() {
                (true, None)
            } else {
                (false, process.child.take())
            }
        };
        if let Some(child) = child {
            let _ = tauri::async_runtime::spawn_blocking(move || child.kill()).await;
        } else if request_sent {
            schedule_force_stop(app, run_id.clone());
        }
        return Err(error);
    }
    Ok(StartResponse { run_id, started_at })
}

#[tauri::command]
async fn check_permissions() -> Result<permissions::PermissionStatus, String> {
    tauri::async_runtime::spawn_blocking(|| permissions::status(true))
        .await
        .map_err(|error| format!("权限检查任务失败：{error}"))
}

#[tauri::command]
async fn request_accessibility_permission() -> Result<permissions::PermissionStatus, String> {
    tauri::async_runtime::spawn_blocking(permissions::request_accessibility)
        .await
        .map_err(|error| format!("授权请求任务失败：{error}"))?
}

impl DataPaths {
    fn clone_for_monitor(&self) -> Self {
        Self {
            config: self.config.clone(),
            progress: self.progress.clone(),
            logs: self.logs.clone(),
        }
    }
}

fn finish_gate(state: &AppState, run_id: &str) {
    state.pending_stop.store(false, Ordering::SeqCst);
    if let Ok(mut gate) = state.gate.lock() {
        gate.finish(run_id);
    }
}

fn request_stop(state: &AppState) -> Result<Option<String>, String> {
    let mut active = state
        .process
        .lock()
        .map_err(|_| "任务进程状态不可用".to_string())?;
    let Some(process) = active.as_mut() else {
        let gate = state
            .gate
            .lock()
            .map_err(|_| "运行状态不可用".to_string())?;
        if let Some(snapshot) = gate.snapshot() {
            let run_id = snapshot.run_id.clone();
            state.pending_stop.store(true, Ordering::SeqCst);
            return Ok(Some(run_id));
        }
        return Ok(None);
    };
    let send_control = process.stop.request_stop();
    if send_control {
        if let Some(child) = process.child.as_mut() {
            // 即使控制管道已关闭也保留停止状态，由宽限期后的进程组清理兜底。
            let _ = child.write(STOP_CONTROL_LINE);
        }
    }
    Ok(Some(process.run_id.clone()))
}

#[tauri::command]
fn stop_run(app: AppHandle, state: State<'_, AppState>) -> Result<bool, String> {
    let Some(run_id) = request_stop(&state)? else {
        return Ok(false);
    };
    let _ = app.emit("stop-requested", json!({"run_id":run_id}));
    schedule_force_stop(app, run_id);
    Ok(true)
}

fn schedule_force_stop(app: AppHandle, run_id: String) {
    tauri::async_runtime::spawn(async move {
        tokio::time::sleep(STOP_GRACE).await;
        let child = {
            let state = app.state::<AppState>();
            let Ok(mut active) = state.process.lock() else {
                return;
            };
            let Some(process) = active.as_mut() else {
                return;
            };
            if process.run_id != run_id || !process.stop.stop_requested() {
                return;
            }
            process.child.take()
        };
        if let Some(child) = child {
            let _ = tauri::async_runtime::spawn_blocking(move || child.kill()).await;
        }
    });
}

async fn monitor_run(
    app: AppHandle,
    paths: DataPaths,
    mut receiver: tauri::async_runtime::Receiver<CommandEvent>,
    run_id: String,
) {
    let mut terminal_event: Option<Value> = None;
    let mut exit_code = None;
    let mut stderr = String::new();
    let mut stdout_buffer = String::new();
    while let Some(event) = receiver.recv().await {
        match event {
            CommandEvent::Stdout(bytes) => {
                stdout_buffer.push_str(&String::from_utf8_lossy(&bytes));
                while let Some(newline) = stdout_buffer.find('\n') {
                    let line = stdout_buffer.drain(..=newline).collect::<String>();
                    process_worker_line(line.trim(), &app, &paths, &run_id, &mut terminal_event);
                }
            }
            CommandEvent::Stderr(bytes) => {
                let line = String::from_utf8_lossy(&bytes).trim().to_string();
                if !line.is_empty() {
                    stderr.push_str(&line);
                    stderr.push('\n');
                    emit_event(
                        &app,
                        &paths,
                        json!({"type":"log", "message":line, "run_id":run_id}),
                    );
                }
            }
            CommandEvent::Error(error) => {
                emit_event(
                    &app,
                    &paths,
                    json!({"type":"error", "message":error, "run_id":run_id}),
                );
            }
            CommandEvent::Terminated(status) => {
                exit_code = status.code;
                break;
            }
            _ => {}
        }
    }
    if !stdout_buffer.trim().is_empty() {
        process_worker_line(
            stdout_buffer.trim(),
            &app,
            &paths,
            &run_id,
            &mut terminal_event,
        );
    }

    let (stop_requested, request_sent) = app
        .state::<AppState>()
        .process
        .lock()
        .ok()
        .and_then(|active| {
            active
                .as_ref()
                .map(|process| (process.stop.stop_requested(), process.stop.request_sent()))
        })
        .unwrap_or((false, false));
    let terminal_status = terminal_event
        .as_ref()
        .and_then(|event| event.get("status"))
        .and_then(Value::as_str);
    let (status, protocol_error) = if stop_requested && !request_sent {
        // 启动闩锁在计划写入前收到停止；worker 没有机会运行，无需报告协议错误。
        ("stopped".to_string(), None)
    } else {
        resolve_worker_status(terminal_status, exit_code, stop_requested)
    };

    let mut progress = read_json::<PersistedProgress>(&paths.progress)
        .ok()
        .flatten()
        .unwrap_or_default();
    progress.status = status.clone();
    progress.finished_at = Some(unix_millis());
    save_progress(&paths, &progress);

    if let Ok(mut active) = app.state::<AppState>().process.lock() {
        if active
            .as_ref()
            .is_some_and(|process| process.run_id == run_id)
        {
            *active = None;
        }
    }
    finish_gate(&app.state::<AppState>(), &run_id);

    let mut event = terminal_event.unwrap_or_else(|| json!({"type":"run_finished"}));
    if let Some(object) = event.as_object_mut() {
        object.insert("run_id".to_string(), json!(run_id));
        object.insert("status".to_string(), json!(status));
        if let Some(error) = protocol_error {
            object.insert("message".to_string(), json!(error));
        } else if object.get("message").is_none() && !stderr.trim().is_empty() {
            object.insert("message".to_string(), json!(stderr.trim()));
        }
    }
    emit_event(&app, &paths, event);
}

fn process_worker_line(
    line: &str,
    app: &AppHandle,
    paths: &DataPaths,
    run_id: &str,
    terminal_event: &mut Option<Value>,
) {
    if line.is_empty() {
        return;
    }
    let Ok(mut value) = serde_json::from_str::<Value>(line) else {
        emit_event(
            app,
            paths,
            json!({"type":"log", "message":line, "run_id":run_id}),
        );
        return;
    };
    if let Some(object) = value.as_object_mut() {
        object.insert("run_id".to_string(), json!(run_id));
    }
    if value.get("type").and_then(Value::as_str) == Some("run_finished") {
        *terminal_event = Some(value);
        return;
    }
    let event_type = value.get("type").and_then(Value::as_str);
    if event_type == Some("task_started") || event_type == Some("task_finished") {
        let task_id = value.get("task_id").and_then(Value::as_str);
        let task_status = value
            .get("status")
            .and_then(Value::as_str)
            .unwrap_or("running");
        if let Ok(Some(mut progress)) = read_json::<PersistedProgress>(&paths.progress) {
            progress.status = "running".to_string();
            if let Some(task_id) = task_id {
                if event_type == Some("task_started") {
                    apply_task_started(&mut progress, task_id);
                } else {
                    apply_task_finished(&mut progress, task_id, task_status);
                }
            }
            save_progress(paths, &progress);
        }
    }
    emit_event(app, paths, value);
}

#[tauri::command]
fn set_always_on_top(window: WebviewWindow, enabled: bool) -> Result<(), String> {
    window
        .set_always_on_top(enabled)
        .map_err(|error| format!("无法调整窗口置顶状态：{error}"))
}

fn stop_shortcut() -> Shortcut {
    Shortcut::new(
        Some(Modifiers::CONTROL | Modifiers::ALT | Modifiers::SUPER),
        Code::KeyK,
    )
}

fn schedule_app_exit(app: AppHandle) {
    tauri::async_runtime::spawn(async move {
        for _ in 0..30 {
            let state = app.state::<AppState>();
            let has_process = state
                .process
                .lock()
                .map(|active| active.is_some())
                .unwrap_or(false);
            let has_starting_run = state
                .gate
                .lock()
                .map(|gate| gate.snapshot().is_some())
                .unwrap_or(false);
            if !has_process && !has_starting_run {
                app.exit(0);
                return;
            }
            tokio::time::sleep(Duration::from_millis(100)).await;
        }
        let run_id = app
            .state::<AppState>()
            .process
            .lock()
            .ok()
            .and_then(|active| active.as_ref().map(|process| process.run_id.clone()));
        if let Some(run_id) = run_id {
            let child = {
                let state = app.state::<AppState>();
                state.process.lock().ok().and_then(|mut active| {
                    active
                        .as_mut()
                        .filter(|process| process.run_id == run_id)
                        .and_then(|process| process.child.take())
                })
            };
            if let Some(child) = child {
                let _ = tauri::async_runtime::spawn_blocking(move || child.kill()).await;
            }
        }
        app.exit(0);
    });
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let shortcut = stop_shortcut();
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_shell::init())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(move |app, pressed, event| {
                    if pressed == &shortcut && event.state() == ShortcutState::Pressed {
                        let state = app.state::<AppState>();
                        match request_stop(&state) {
                            Ok(Some(run_id)) => {
                                let _ = app.emit("stop-requested", json!({"run_id":run_id}));
                                schedule_force_stop(app.clone(), run_id);
                            }
                            Ok(None) => {}
                            Err(error) => {
                                let _ = app
                                    .emit("worker-event", json!({"type":"error", "message":error}));
                            }
                        }
                    }
                })
                .build(),
        )
        .setup(|app| {
            let app_data_dir = app.path().app_data_dir()?;
            let state =
                AppState::initialize(app_data_dir).map_err(|error| std::io::Error::other(error))?;
            app.manage(state);
            if let Err(error) = app.global_shortcut().register(stop_shortcut()) {
                eprintln!("全局停止快捷键不可用（⌃⌥⌘K）：{error}");
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_catalog,
            load_app_state,
            save_config,
            restore_defaults,
            check_permissions,
            request_accessibility_permission,
            start_run,
            stop_run,
            set_always_on_top
        ])
        .build(tauri::generate_context!())
        .expect("构建 Tauri 桌面应用失败")
        .run(|app, event| {
            if let RunEvent::ExitRequested { api, .. } = event {
                let state = app.state::<AppState>();
                match request_stop(&state) {
                    Ok(Some(run_id)) => {
                        api.prevent_exit();
                        let _ = app.emit("stop-requested", json!({"run_id":run_id}));
                        if !state.shutdown_started.swap(true, Ordering::SeqCst) {
                            schedule_app_exit(app.clone());
                        }
                    }
                    Ok(None) => {}
                    Err(error) => {
                        api.prevent_exit();
                        let _ = app.emit("worker-event", json!({"type":"error", "message":error}));
                        if !state.shutdown_started.swap(true, Ordering::SeqCst) {
                            schedule_app_exit(app.clone());
                        }
                    }
                }
            }
        });
}
