use serde::Serialize;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum PermissionState {
    Granted,
    Denied,
    NeedsAuthorization,
    NotChecked,
    TimedOut,
    Unavailable,
    Unsupported,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct PermissionStatus {
    pub platform: &'static str,
    pub accessibility: PermissionState,
    pub automation: PermissionState,
}

/// macOS 的原生权限查询与请求；其他平台只返回模拟可识别的状态，不调用系统设置。
#[cfg(target_os = "macos")]
mod platform {
    use super::{PermissionState, PermissionStatus};
    use std::{
        ffi::c_void,
        process::{Command, Stdio},
        thread,
        time::{Duration, Instant},
    };

    const ACCESSIBILITY_SETTINGS_URL: &str =
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility";
    const AUTOMATION_SETTINGS_URL: &str =
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation";
    const SYSTEM_EVENTS_BUNDLE_ID: &[u8] = b"com.apple.systemevents";
    const AUTOMATION_QUERY_TIMEOUT: Duration = Duration::from_secs(30);
    const ERR_AE_EVENT_NOT_PERMITTED: i32 = -1743;
    const ERR_AE_EVENT_WOULD_REQUIRE_USER_CONSENT: i32 = -1744;
    const ERR_PROCESS_NOT_FOUND: i32 = -600;

    #[repr(C)]
    struct AeDesc {
        descriptor_type: u32,
        data_handle: *mut c_void,
    }

    #[link(name = "ApplicationServices", kind = "framework")]
    extern "C" {
        static kAXTrustedCheckOptionPrompt: *const c_void;
        fn AXIsProcessTrustedWithOptions(options: *const c_void) -> u8;
    }

    #[link(name = "CoreFoundation", kind = "framework")]
    extern "C" {
        static kCFBooleanTrue: *const c_void;
        fn CFDictionaryCreate(
            allocator: *const c_void,
            keys: *const *const c_void,
            values: *const *const c_void,
            count: isize,
            key_callbacks: *const c_void,
            value_callbacks: *const c_void,
        ) -> *const c_void;
        fn CFRelease(value: *const c_void);
    }

    #[link(name = "Carbon", kind = "framework")]
    extern "C" {
        fn AECreateDesc(
            descriptor_type: u32,
            data: *const c_void,
            data_size: isize,
            result: *mut AeDesc,
        ) -> i16;
        fn AEDisposeDesc(desc: *mut AeDesc) -> i16;
        fn AEDeterminePermissionToAutomateTarget(
            target: *const AeDesc,
            event_class: u32,
            event_id: u32,
            ask_user_if_needed: u8,
        ) -> i32;
    }

    fn accessibility_trusted(prompt: bool) -> Result<bool, String> {
        if !prompt {
            return Ok(unsafe { AXIsProcessTrustedWithOptions(std::ptr::null()) != 0 });
        }

        unsafe {
            let keys = [kAXTrustedCheckOptionPrompt];
            let values = [kCFBooleanTrue];
            let options = CFDictionaryCreate(
                std::ptr::null(),
                keys.as_ptr(),
                values.as_ptr(),
                1,
                std::ptr::null(),
                std::ptr::null(),
            );
            if options.is_null() {
                return Err("无法创建辅助功能权限请求参数".to_string());
            }
            let trusted = AXIsProcessTrustedWithOptions(options) != 0;
            CFRelease(options);
            Ok(trusted)
        }
    }

    fn automation_permission_without_prompt() -> Result<(), i32> {
        let mut target = AeDesc {
            descriptor_type: 0,
            data_handle: std::ptr::null_mut(),
        };
        let create_status = unsafe {
            AECreateDesc(
                u32::from_be_bytes(*b"bund"),
                SYSTEM_EVENTS_BUNDLE_ID.as_ptr().cast(),
                SYSTEM_EVENTS_BUNDLE_ID.len() as isize,
                &mut target,
            )
        };
        if create_status != 0 {
            return Err(i32::from(create_status));
        }

        // ask_user_if_needed=false 只读取授权状态，目标进程未运行时返回 -600。
        let status = unsafe {
            AEDeterminePermissionToAutomateTarget(
                &target,
                u32::from_be_bytes(*b"core"),
                u32::from_be_bytes(*b"getd"),
                0,
            )
        };
        unsafe {
            AEDisposeDesc(&mut target);
        }
        if status == 0 {
            Ok(())
        } else {
            Err(status)
        }
    }

    fn query_system_events_readonly() -> PermissionState {
        let mut child = match Command::new("/usr/bin/osascript")
            .args([
                "-e",
                "tell application id \"com.apple.systemevents\" to get count of application processes",
            ])
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
        {
            Ok(child) => child,
            Err(_) => return PermissionState::Unavailable,
        };

        let started = Instant::now();
        loop {
            match child.try_wait() {
                Ok(Some(status)) => {
                    return if status.success() {
                        PermissionState::Granted
                    } else {
                        PermissionState::Denied
                    };
                }
                Ok(None) if started.elapsed() < AUTOMATION_QUERY_TIMEOUT => {
                    thread::sleep(Duration::from_millis(25));
                }
                Ok(None) => {
                    let _ = child.kill();
                    let _ = child.wait();
                    return PermissionState::TimedOut;
                }
                Err(_) => {
                    let _ = child.kill();
                    let _ = child.wait();
                    return PermissionState::Unavailable;
                }
            }
        }
    }

    fn open_settings(url: &str) -> Result<(), String> {
        let status = Command::new("/usr/bin/open")
            .arg(url)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .map_err(|error| format!("无法打开 macOS 授权设置：{error}"))?;
        if !status.success() {
            return Err("无法打开 macOS 授权设置".to_string());
        }
        Ok(())
    }

    fn automation_status(request_if_needed: bool) -> PermissionState {
        match automation_permission_without_prompt() {
            Ok(()) => query_system_events_readonly(),
            Err(ERR_PROCESS_NOT_FOUND | ERR_AE_EVENT_WOULD_REQUIRE_USER_CONSENT)
                if request_if_needed =>
            {
                // 仅由显式授权或实时启动调用；查询只读，但 macOS 可能显示 Apple Events 授权提示。
                query_system_events_readonly()
            }
            Err(ERR_PROCESS_NOT_FOUND) => PermissionState::NotChecked,
            Err(ERR_AE_EVENT_WOULD_REQUIRE_USER_CONSENT) => PermissionState::NeedsAuthorization,
            Err(ERR_AE_EVENT_NOT_PERMITTED) => PermissionState::Denied,
            Err(_) => PermissionState::Unavailable,
        }
    }

    fn permission_status(check_automation: bool, request_if_needed: bool) -> PermissionStatus {
        let accessibility = match accessibility_trusted(false) {
            Ok(true) => PermissionState::Granted,
            Ok(false) => PermissionState::Denied,
            Err(_) => PermissionState::Unavailable,
        };
        let automation = if accessibility != PermissionState::Granted || !check_automation {
            PermissionState::NotChecked
        } else {
            automation_status(request_if_needed)
        };
        PermissionStatus {
            platform: "macos",
            accessibility,
            automation,
        }
    }

    pub fn status(check_automation: bool) -> PermissionStatus {
        permission_status(check_automation, false)
    }

    pub fn request_accessibility() -> Result<PermissionStatus, String> {
        // 仅由显式授权按钮调用；系统提示异步出现，应用不能代替用户打开开关。
        if !accessibility_trusted(true)? {
            open_settings(ACCESSIBILITY_SETTINGS_URL)?;
            return Ok(status(false));
        }
        let current = permission_status(true, true);
        if matches!(
            current.automation,
            PermissionState::Denied
                | PermissionState::NeedsAuthorization
                | PermissionState::TimedOut
        ) {
            open_settings(AUTOMATION_SETTINGS_URL)?;
        }
        Ok(current)
    }

    pub fn live_preflight() -> Result<(), String> {
        let accessibility = accessibility_trusted(false)
            .map_err(|error| format!("无法读取辅助功能权限：{error}"))?;
        if !accessibility {
            request_accessibility()?;
            return Err(
                "辅助功能尚未授权。已请求 macOS 权限提示并打开设置；请手动开启后重试。".to_string(),
            );
        }

        let automation = automation_status(true);
        if matches!(
            automation,
            PermissionState::Denied
                | PermissionState::NeedsAuthorization
                | PermissionState::TimedOut
        ) {
            open_settings(AUTOMATION_SETTINGS_URL)?;
        }
        super::check_live_permissions(false, PermissionState::Granted, automation)
    }
}

#[cfg(target_os = "windows")]
mod platform {
    use super::{PermissionState, PermissionStatus};

    pub fn status(_check_automation: bool) -> PermissionStatus {
        PermissionStatus {
            platform: "windows",
            accessibility: PermissionState::Unsupported,
            automation: PermissionState::Unsupported,
        }
    }

    pub fn request_accessibility() -> Result<PermissionStatus, String> {
        Ok(status(false))
    }

    pub fn live_preflight() -> Result<(), String> {
        Err("Windows 实时输入尚未实现；当前只能运行模拟流程".to_string())
    }
}

#[cfg(not(any(target_os = "macos", target_os = "windows")))]
mod platform {
    use super::{PermissionState, PermissionStatus};

    pub fn status(_check_automation: bool) -> PermissionStatus {
        PermissionStatus {
            platform: "other",
            accessibility: PermissionState::Unsupported,
            automation: PermissionState::Unsupported,
        }
    }

    pub fn request_accessibility() -> Result<PermissionStatus, String> {
        Ok(status(false))
    }

    pub fn live_preflight() -> Result<(), String> {
        Err("当前平台不支持实时输入".to_string())
    }
}

pub use platform::{live_preflight, request_accessibility, status};

pub fn check_live_permissions(
    dry_run: bool,
    accessibility: PermissionState,
    automation: PermissionState,
) -> Result<(), String> {
    if dry_run {
        return Ok(());
    }
    if accessibility != PermissionState::Granted {
        return Err("辅助功能尚未授权；实时任务未启动".to_string());
    }
    if automation != PermissionState::Granted {
        return Err("System Events 自动化尚未授权；实时任务未启动".to_string());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{check_live_permissions, PermissionState};

    #[test]
    fn dry_run_is_not_blocked_by_missing_macos_permissions() {
        assert!(
            check_live_permissions(true, PermissionState::Denied, PermissionState::NotChecked)
                .is_ok()
        );
    }

    #[test]
    fn live_run_requires_accessibility_before_automation() {
        let error =
            check_live_permissions(false, PermissionState::Denied, PermissionState::Granted)
                .unwrap_err();
        assert!(error.contains("辅助功能"));
    }

    #[test]
    fn live_run_requires_system_events_automation_too() {
        let error =
            check_live_permissions(false, PermissionState::Granted, PermissionState::NotChecked)
                .unwrap_err();
        assert!(error.contains("Automation") || error.contains("自动化"));
    }

    #[test]
    fn live_run_passes_only_when_both_permissions_are_granted() {
        assert!(
            check_live_permissions(false, PermissionState::Granted, PermissionState::Granted)
                .is_ok()
        );
    }
}
