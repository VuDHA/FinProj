// Wealth VN — Tauri desktop wrapper.
//
// Responsibilities:
//   1. Spawn the PyInstaller-bundled FastAPI sidecar (`wealth-backend`).
//   2. Wait for the backend health endpoint before showing the window.
//   3. Capture sidecar stdout/stderr into a log file.
//   4. Tear down the sidecar cleanly on window close.
//   5. Expose Tauri commands for auto-update checks/installs and backend URL.
//
// Windows-only for now (Vietnamese user base).

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs::OpenOptions;
use std::io::Write;
use std::sync::Mutex;
use std::time::Duration;

use log::{error, info, warn};
use serde::Serialize;
use tauri::{Emitter, Manager};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_updater::UpdaterExt;

/// Target triple used by Tauri sidecars on Windows x64.
const SIDECAR_TARGET: &str = "x86_64-pc-windows-msvc";

/// Base URL for the embedded FastAPI backend.
const BACKEND_URL: &str = "http://127.0.0.1:8000";

/// How long to wait for the backend health check before giving up.
const HEALTH_TIMEOUT: Duration = Duration::from_secs(30);

/// Interval between health check polls.
const HEALTH_POLL_INTERVAL: Duration = Duration::from_millis(500);

/// Grace period for the sidecar to exit before force-killing it.
const KILL_TIMEOUT: Duration = Duration::from_secs(5);

/// Information about an available update, returned to the frontend.
#[derive(Debug, Serialize)]
pub struct UpdateInfo {
    pub version: String,
    pub notes: String,
    pub date: Option<String>,
}

/// State shared across Tauri commands: the spawned sidecar handle.
struct AppState {
    sidecar: Mutex<Option<CommandChild>>,
}

/// Resolve the data directory used by the backend.
///
/// Layout: `<app_config_dir>/wealth-vn/data`
fn resolve_data_dir(app: &tauri::AppHandle) -> Result<String, String> {
    let config_dir = app
        .path()
        .app_config_dir()
        .map_err(|e| format!("Không thể lấy thư mục cấu hình ứng dụng: {}", e))?;
    let data_dir = config_dir.join("wealth-vn").join("data");
    std::fs::create_dir_all(&data_dir)
        .map_err(|e| format!("Không thể tạo thư mục dữ liệu: {}", e))?;
    Ok(data_dir.to_string_lossy().into_owned())
}

/// Open (or create) a log file in the config dir and return its path.
fn open_log_file(app: &tauri::AppHandle) -> Result<(std::fs::File, String), String> {
    let config_dir = app
        .path()
        .app_config_dir()
        .map_err(|e| format!("Không thể lấy thư mục cấu hình ứng dụng: {}", e))?;
    std::fs::create_dir_all(&config_dir)
        .map_err(|e| format!("Không thể tạo thư mục cấu hình: {}", e))?;
    let log_path = config_dir.join("backend.log");
    let file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_path)
        .map_err(|e| format!("Không thể mở file log: {}", e))?;
    Ok((file, log_path.to_string_lossy().into_owned()))
}

/// Spawn the `wealth-backend` sidecar with the required environment.
fn spawn_sidecar(
    app: &tauri::AppHandle,
    data_dir: &str,
    log_file: std::fs::File,
) -> Result<CommandChild, String> {
    let sidecar_name = format!("wealth-backend-{}", SIDECAR_TARGET);
    let shell = app.shell();

    let mut command = shell
        .sidecar(&sidecar_name)
        .map_err(|e| format!("Không tìm thấy sidecar '{}': {}", sidecar_name, e))?;

    command = command.env("WEALTH_DATA_DIR", data_dir);

    let (mut rx, child) = command
        .spawn()
        .map_err(|e| format!("Không thể khởi động backend: {}", e))?;

    // Drain stdout/stderr events into the log file on a background thread.
    let mut log_file = log_file;
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            let line = match event {
                tauri_plugin_shell::process::CommandEvent::Stdout(bytes) => {
                    String::from_utf8_lossy(&bytes).into_owned()
                }
                tauri_plugin_shell::process::CommandEvent::Stderr(bytes) => {
                    String::from_utf8_lossy(&bytes).into_owned()
                }
                tauri_plugin_shell::process::CommandEvent::Terminated(payload) => {
                    let msg = format!(
                        "[sidecar terminated: code={:?}, signal={:?}]\n",
                        payload.code, payload.signal
                    );
                    let _ = writeln!(log_file, "{}", msg.trim_end());
                    let _ = log_file.flush();
                    warn!("{}", msg.trim_end());
                    break;
                }
                _ => continue,
            };
            if !line.is_empty() {
                let _ = write!(log_file, "{}", line);
                let _ = log_file.flush();
            }
        }
    });

    info!("Sidecar '{}' đã khởi động", sidecar_name);
    Ok(child)
}

/// Poll the backend `/health` endpoint until it responds or timeout.
async fn wait_for_backend() -> Result<(), String> {
    let client = reqwest::Client::builder()
        .timeout(HEALTH_POLL_INTERVAL)
        .build()
        .map_err(|e| format!("Không tạo được HTTP client: {}", e))?;

    let deadline = std::time::Instant::now() + HEALTH_TIMEOUT;
    let url = format!("{}/health", BACKEND_URL);

    loop {
        if std::time::Instant::now() > deadline {
            return Err(format!(
                "Backend không phản hồi sau {} giây.",
                HEALTH_TIMEOUT.as_secs()
            ));
        }
        match client.get(&url).send().await {
            Ok(resp) if resp.status().is_success() => {
                info!("Backend đã sẵn sàng tại {}", BACKEND_URL);
                return Ok(());
            }
            _ => {
                tokio::time::sleep(HEALTH_POLL_INTERVAL).await;
            }
        }
    }
}

/// Terminate the sidecar: graceful first, force-kill after `KILL_TIMEOUT`.
fn kill_sidecar(state: &AppState) {
    let child_opt = state.sidecar.lock().unwrap().take();
    if let Some(child) = child_opt {
        // Request graceful termination.
        if let Err(e) = child.kill() {
            warn!("Không thể gửi tín hiệu kết thúc tới backend: {}", e);
        }
        // Best-effort wait; CommandChild does not expose a blocking wait, so
        // we rely on the Terminated event arriving within the grace period.
        let deadline = std::time::Instant::now() + KILL_TIMEOUT;
        while std::time::Instant::now() < deadline {
            std::thread::sleep(Duration::from_millis(100));
        }
        info!("Đã dừng backend sidecar.");
    }
}

/// Tauri command: return the backend base URL so the frontend can call the API.
#[tauri::command]
fn get_backend_url() -> String {
    BACKEND_URL.to_string()
}

/// Tauri command: check for an available app update.
#[tauri::command]
async fn check_for_updates(app: tauri::AppHandle) -> Result<Option<UpdateInfo>, String> {
    let updater = app
        .updater()
        .map_err(|e| format!("Không lấy được updater: {}", e))?;
    match updater.check().await {
        Ok(Some(update)) => {
            info!("Có bản cập nhật: {}", update.version);
            Ok(Some(UpdateInfo {
                version: update.version.clone(),
                notes: update.body.clone().unwrap_or_default(),
                date: update.date.map(|d| d.to_string()),
            }))
        }
        Ok(None) => {
            info!("Không có bản cập nhật mới.");
            Ok(None)
        }
        Err(e) => {
            error!("Lỗi khi kiểm tra cập nhật: {}", e);
            Err(format!("Lỗi khi kiểm tra cập nhật: {}", e))
        }
    }
}

/// Tauri command: download + install the pending update, then restart.
#[tauri::command]
async fn install_update(app: tauri::AppHandle) -> Result<(), String> {
    let updater = app
        .updater()
        .map_err(|e| format!("Không lấy được updater: {}", e))?;
    let update = updater
        .check()
        .await
        .map_err(|e| format!("Không kiểm tra được cập nhật: {}", e))?
        .ok_or_else(|| "Không có bản cập nhật để cài đặt.".to_string())?;

    info!("Đang tải bản cập nhật {}...", update.version);
    update
        .download_and_install(|_, _| {}, || {})
        .await
        .map_err(|e| format!("Lỗi khi tải/cài đặt cập nhật: {}", e))?;
    info!("Cập nhật xong, đang khởi động lại ứng dụng.");
    app.request_restart();
    Ok(())
}

fn main() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .setup(|app| {
            let app_handle = app.handle().clone();

            // Resolve data dir + open log file before spawning the sidecar.
            let data_dir = resolve_data_dir(&app_handle)?;
            let (log_file, log_path) = open_log_file(&app_handle)?;
            info!("File log backend: {}", log_path);
            info!("Thư mục dữ liệu: {}", data_dir);

            let child = spawn_sidecar(&app_handle, &data_dir, log_file)?;

            // Store the sidecar handle in managed state.
            app.manage(AppState {
                sidecar: Mutex::new(Some(child)),
            });

            // Wait for the backend to become healthy before showing the window.
            let main_window = app
                .get_webview_window("main")
                .ok_or_else(|| "Không tìm thấy cửa sổ chính.".to_string())?;

            // Hide until ready; show after health check passes.
            main_window
                .hide()
                .map_err(|e| format!("Không ẩn được cửa sổ: {}", e))?;

            let handle_for_wait = app_handle.clone();
            let window_for_show = main_window.clone();
            tauri::async_runtime::spawn(async move {
                match wait_for_backend().await {
                    Ok(()) => {
                        if let Err(e) = window_for_show.show() {
                            error!("Không hiển thị được cửa sổ: {}", e);
                        }
                        if let Err(e) = window_for_show.set_focus() {
                            warn!("Không focus được cửa sổ: {}", e);
                        }
                    }
                    Err(msg) => {
                        error!("{}", msg);
                        // Show the window anyway so the user sees an error screen.
                        let _ = window_for_show.show();
                        let _ = window_for_show.set_focus();
                        let _ = window_for_show.emit("backend-error", msg.clone());
                        let _ = handle_for_wait.emit("backend-error", msg);
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let state = window.app_handle().state::<AppState>();
                kill_sidecar(state.inner());
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_url,
            check_for_updates,
            install_update,
        ])
        .run(tauri::generate_context!())
        .expect("Lỗi khi chạy ứng dụng Wealth VN");
}
