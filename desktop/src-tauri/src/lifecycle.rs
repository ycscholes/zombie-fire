use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
pub struct RunRequest {
    pub mode: String,
    pub task_ids: Vec<String>,
    pub from_task: Option<String>,
    pub command: String,
    pub args: Vec<String>,
    #[serde(default)]
    pub phase_args: HashMap<String, Vec<String>>,
    pub dry_run: bool,
}

#[derive(Clone, Debug, PartialEq)]
pub struct RunSnapshot {
    pub run_id: String,
    pub mode: String,
    pub task_ids: Vec<String>,
    pub from_task: Option<String>,
    pub command: Option<String>,
    pub args: Vec<String>,
    pub phase_args: HashMap<String, Vec<String>>,
    pub dry_run: bool,
}

impl RunSnapshot {
    pub fn capture(run_id: String, request: &RunRequest) -> Self {
        Self {
            run_id,
            mode: request.mode.clone(),
            task_ids: request.task_ids.clone(),
            from_task: request.from_task.clone(),
            command: (request.mode == "command").then(|| request.command.clone()),
            args: request.args.clone(),
            phase_args: request.phase_args.clone(),
            dry_run: request.dry_run,
        }
    }
}

#[derive(Default)]
pub struct RunGate {
    active: Option<RunSnapshot>,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct WorkerStopState {
    stop_requested: bool,
    request_sent: bool,
}

impl WorkerStopState {
    pub fn new(stop_latched_before_spawn: bool) -> Self {
        Self {
            stop_requested: stop_latched_before_spawn,
            request_sent: false,
        }
    }

    pub fn stop_requested(&self) -> bool {
        self.stop_requested
    }

    pub fn request_sent(&self) -> bool {
        self.request_sent
    }

    pub fn may_send_initial_request(&self) -> bool {
        !self.stop_requested
    }

    pub fn mark_request_sent(&mut self) {
        self.request_sent = true;
    }

    /// 返回 true 表示停止发生在计划发送之后，需要写一条控制行。
    pub fn request_stop(&mut self) -> bool {
        if self.stop_requested {
            return false;
        }
        self.stop_requested = true;
        self.request_sent
    }
}

impl RunGate {
    pub fn begin(&mut self, snapshot: RunSnapshot) -> Result<(), String> {
        if self.active.is_some() {
            return Err("已有任务仍在运行，请等待它结束".to_string());
        }
        self.active = Some(snapshot);
        Ok(())
    }

    pub fn snapshot(&self) -> Option<&RunSnapshot> {
        self.active.as_ref()
    }

    pub fn finish(&mut self, run_id: &str) -> bool {
        if self
            .active
            .as_ref()
            .is_some_and(|active| active.run_id == run_id)
        {
            self.active = None;
            true
        } else {
            false
        }
    }
}

#[derive(Clone, Debug, Default, Deserialize, Serialize, PartialEq)]
#[serde(default)]
pub struct PersistedProgress {
    pub status: String,
    pub current_task_id: Option<String>,
    pub last_finished_task_id: Option<String>,
    pub last_task_status: Option<String>,
    pub run_id: Option<String>,
    pub started_at: Option<u64>,
    pub finished_at: Option<u64>,
}

pub fn apply_task_started(progress: &mut PersistedProgress, task_id: &str) {
    progress.current_task_id = Some(task_id.to_string());
    progress.last_task_status = Some("running".to_string());
}

pub fn apply_task_finished(progress: &mut PersistedProgress, task_id: &str, status: &str) {
    progress.last_task_status = Some(status.to_string());
    if status == "completed" || status == "skipped" {
        progress.current_task_id = None;
        progress.last_finished_task_id = Some(task_id.to_string());
    } else {
        // 失败或停止的任务可从任务开头重试，不能误标为已完成。
        progress.current_task_id = Some(task_id.to_string());
    }
}

pub fn recover_progress(mut progress: PersistedProgress) -> PersistedProgress {
    if progress.status == "running" {
        progress.status = "interrupted".to_string();
    }
    progress
}

pub fn resolve_worker_status(
    terminal_status: Option<&str>,
    exit_code: Option<i32>,
    stop_requested: bool,
) -> (String, Option<String>) {
    match (terminal_status, exit_code) {
        (Some("completed"), Some(0)) => ("completed".to_string(), None),
        (Some("dry_run_completed"), Some(0)) => ("dry_run_completed".to_string(), None),
        (Some("stopped"), Some(0)) => ("stopped".to_string(), None),
        (Some("failed"), Some(0)) => ("failed".to_string(), None),
        (Some("failed"), Some(_)) => ("failed".to_string(), None),
        (Some(value), Some(code)) => (
            "failed".to_string(),
            Some(format!("sidecar 声明状态为 {value}，但退出码为 {code}。")),
        ),
        (None, Some(0)) => (
            "failed".to_string(),
            Some("sidecar 未发送有效的 run_finished 终止事件。".to_string()),
        ),
        (None, Some(_)) if stop_requested => (
            "stopped".to_string(),
            Some("sidecar 未能在停止宽限期内完成，已强制结束进程组。".to_string()),
        ),
        (_, None) if stop_requested => (
            "stopped".to_string(),
            Some("停止请求已送达，sidecar 在返回退出码前结束。".to_string()),
        ),
        (_, Some(code)) => (
            "failed".to_string(),
            Some(format!("sidecar 异常退出，退出码：{code}。")),
        ),
        (_, None) => (
            "failed".to_string(),
            Some("sidecar 终止事件缺少退出码。".to_string()),
        ),
    }
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;

    use super::{
        apply_task_finished, apply_task_started, recover_progress, resolve_worker_status,
        PersistedProgress, RunGate, RunRequest, RunSnapshot, WorkerStopState,
    };

    fn snapshot(id: &str, task_ids: &[&str]) -> RunSnapshot {
        RunSnapshot {
            run_id: id.to_string(),
            mode: "daily".to_string(),
            task_ids: task_ids.iter().map(|value| value.to_string()).collect(),
            from_task: task_ids.first().map(|value| value.to_string()),
            command: None,
            args: Vec::new(),
            phase_args: HashMap::new(),
            dry_run: true,
        }
    }

    #[test]
    fn active_run_uses_a_locked_plan_snapshot() {
        let mut gate = RunGate::default();
        let mut editable_config = vec!["daily-a".to_string(), "daily-b".to_string()];
        let captured = snapshot("run-1", &["daily-a", "daily-b"]);
        gate.begin(captured).unwrap();

        editable_config.remove(0);

        assert_eq!(editable_config, ["daily-b"]);
        assert_eq!(gate.snapshot().unwrap().task_ids, ["daily-a", "daily-b"]);
    }

    #[test]
    fn active_run_snapshot_keeps_the_phase_argument_snapshot() {
        let request = RunRequest {
            mode: "daily".to_string(),
            task_ids: vec!["mechanical.shock".to_string()],
            from_task: Some("mechanical.shock".to_string()),
            command: String::new(),
            args: Vec::new(),
            phase_args: HashMap::from([(
                "mechanical_shock".to_string(),
                vec!["--mechanical-shock-task-claims".to_string(), "0".to_string()],
            )]),
            dry_run: true,
        };

        let snapshot = RunSnapshot::capture("run-args".to_string(), &request);

        assert_eq!(snapshot.phase_args["mechanical_shock"][1], "0");
    }

    #[test]
    fn older_run_requests_without_phase_arguments_still_deserialize() {
        let request: RunRequest = serde_json::from_str(
            r#"{"mode":"daily","task_ids":[],"from_task":null,"command":"","args":[],"dry_run":true}"#,
        )
        .unwrap();

        assert!(request.phase_args.is_empty());
    }

    #[test]
    fn a_new_run_stays_blocked_until_the_active_run_is_terminal() {
        let mut gate = RunGate::default();
        gate.begin(snapshot("run-1", &["daily-a"])).unwrap();

        assert!(gate.begin(snapshot("run-2", &["daily-b"])).is_err());
        assert!(!gate.finish("run-2"));
        assert!(gate.snapshot().is_some());

        assert!(gate.finish("run-1"));
        assert!(gate.begin(snapshot("run-2", &["daily-b"])).is_ok());
    }

    #[test]
    fn persisted_running_progress_becomes_interrupted_without_auto_resume() {
        let saved = PersistedProgress {
            status: "running".to_string(),
            current_task_id: Some("calendar".to_string()),
            last_finished_task_id: None,
            last_task_status: Some("running".to_string()),
            run_id: Some("old-run".to_string()),
            started_at: Some(1_792_000_000_000),
            finished_at: None,
        };

        let recovered = recover_progress(saved);

        assert_eq!(recovered.status, "interrupted");
        assert_eq!(recovered.current_task_id.as_deref(), Some("calendar"));
        assert_eq!(recovered.run_id.as_deref(), Some("old-run"));
        assert!(recovered.finished_at.is_none());
    }

    #[test]
    fn persisted_progress_tracks_task_start_and_completion_boundaries() {
        let mut progress = PersistedProgress::default();
        apply_task_started(&mut progress, "calendar");
        assert_eq!(progress.current_task_id.as_deref(), Some("calendar"));
        assert_eq!(progress.last_task_status.as_deref(), Some("running"));

        apply_task_finished(&mut progress, "calendar", "completed");
        assert!(progress.current_task_id.is_none());
        assert_eq!(progress.last_finished_task_id.as_deref(), Some("calendar"));
        assert_eq!(progress.last_task_status.as_deref(), Some("completed"));

        apply_task_started(&mut progress, "welfare");
        apply_task_finished(&mut progress, "welfare", "failed");
        assert_eq!(progress.current_task_id.as_deref(), Some("welfare"));
        assert_eq!(progress.last_task_status.as_deref(), Some("failed"));
        assert_eq!(progress.last_finished_task_id.as_deref(), Some("calendar"));

        apply_task_finished(&mut progress, "welfare", "skipped");
        assert!(progress.current_task_id.is_none());
        assert_eq!(progress.last_finished_task_id.as_deref(), Some("welfare"));
    }

    #[test]
    fn successful_terminal_status_requires_a_valid_event_and_zero_exit() {
        assert_eq!(
            resolve_worker_status(Some("dry_run_completed"), Some(0), false),
            ("dry_run_completed".to_string(), None)
        );
        let mismatch = resolve_worker_status(Some("completed"), Some(1), false);
        assert_eq!(mismatch.0, "failed");
        assert!(mismatch.1.is_some());
        assert_eq!(resolve_worker_status(None, Some(0), false).0, "failed");
        assert_eq!(resolve_worker_status(None, Some(1), true).0, "stopped");
        assert_eq!(resolve_worker_status(None, None, true).0, "stopped");
    }

    #[test]
    fn failed_terminal_status_with_nonzero_exit_is_not_a_status_conflict() {
        assert_eq!(
            resolve_worker_status(Some("failed"), Some(1), false),
            ("failed".to_string(), None)
        );
    }

    #[test]
    fn completed_or_stopped_status_with_nonzero_exit_remains_a_conflict() {
        assert_eq!(
            resolve_worker_status(Some("completed"), Some(1), false),
            (
                "failed".to_string(),
                Some("sidecar 声明状态为 completed，但退出码为 1。".to_string())
            )
        );
        assert_eq!(
            resolve_worker_status(Some("stopped"), Some(1), false),
            (
                "failed".to_string(),
                Some("sidecar 声明状态为 stopped，但退出码为 1。".to_string())
            )
        );
    }

    #[test]
    fn a_stop_latched_before_request_suppresses_worker_execution() {
        let mut control = WorkerStopState::new(true);

        assert!(!control.may_send_initial_request());
        assert!(!control.request_sent());
        assert!(!control.request_stop());
    }

    #[test]
    fn a_stop_after_process_reservation_but_before_request_suppresses_execution() {
        let mut control = WorkerStopState::new(false);

        assert!(!control.request_stop());
        assert!(!control.may_send_initial_request());
        assert!(!control.request_sent());
    }

    #[test]
    fn a_stop_after_request_sends_one_ordered_control_line() {
        let mut control = WorkerStopState::new(false);
        assert!(control.may_send_initial_request());
        control.mark_request_sent();

        assert!(control.request_stop());
        assert!(!control.request_stop());
        assert!(control.request_sent());
        assert!(control.stop_requested());
    }
}
