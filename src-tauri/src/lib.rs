use std::sync::Mutex;
use std::time::Duration;

use serde::Serialize;
use tauri::{AppHandle, Emitter, State, Manager};
use tauri::menu::{Menu, MenuItem};
use tauri::tray::{TrayIconBuilder, TrayIconEvent};
use tauri_plugin_global_shortcut::{Code, Modifiers, Shortcut, ShortcutState, GlobalShortcutExt};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const BACKEND_PORT: u16 = 8000;
const BACKEND_HOST: &str = "127.0.0.1";

#[derive(Default)]
struct BackendProcess {
    child: Mutex<Option<CommandChild>>,
}

#[derive(Serialize)]
struct BackendStatus {
    running: bool,
    host: String,
    port: u16,
    health: serde_json::Value,
}

#[derive(Serialize)]
struct GpuProfile {
    name: String,
    vram_gb: f64,
}

#[tauri::command]
async fn get_gpu_info() -> Result<Vec<GpuProfile>, String> {
    let output = std::process::Command::new("powershell")
        .args([
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Json"
        ])
        .output()
        .map_err(|e| format!("Failed to run powershell: {e}"))?;

    if !output.status.success() {
        let err = String::from_utf8_lossy(&output.stderr);
        return Err(format!("PowerShell command failed: {err}"));
    }

    let stdout_str = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if stdout_str.is_empty() {
        return Ok(vec![]);
    }

    let parsed: serde_json::Value = serde_json::from_str(&stdout_str)
        .map_err(|e| format!("Failed to parse JSON: {e}"))?;

    let items = if let Some(arr) = parsed.as_array() {
        arr.clone()
    } else {
        vec![parsed]
    };

    let mut gpus = Vec::new();
    for item in items {
        if let Some(obj) = item.as_object() {
            let name = obj.get("Name")
                .and_then(|v| v.as_str())
                .unwrap_or("Unknown GPU")
                .to_string();
            let ram_bytes = obj.get("AdapterRAM")
                .and_then(|v| v.as_f64().or_else(|| v.as_i64().map(|i| i as f64)))
                .unwrap_or(0.0);
            let vram_gb = (ram_bytes / (1024.0 * 1024.0 * 1024.0) * 10.0).round() / 10.0;
            gpus.push(GpuProfile { name, vram_gb });
        }
    }

    Ok(gpus)
}

#[tauri::command]
async fn pick_rag_file() -> Result<Option<String>, String> {
    let file = rfd::AsyncFileDialog::new()
        .set_title("Выберите файл для добавления в RAG Vault")
        .add_filter("Документы", &["pdf", "docx", "txt", "md"])
        .pick_file()
        .await;

    if let Some(file_handle) = file {
        Ok(Some(file_handle.path().to_string_lossy().to_string()))
    } else {
        Ok(None)
    }
}

#[tauri::command]
async fn install_ollama() -> Result<String, String> {
    let url = "https://ollama.com/download/OllamaSetup.exe";
    let temp_dir = std::env::temp_dir();
    let installer_path = temp_dir.join("OllamaSetup.exe");

    let response = reqwest::get(url)
        .await
        .map_err(|e| format!("Failed to connect to ollama.com: {e}"))?;

    let bytes = response.bytes()
        .await
        .map_err(|e| format!("Failed to download Ollama installer: {e}"))?;

    std::fs::write(&installer_path, bytes)
        .map_err(|e| format!("Failed to save installer file: {e}"))?;

    std::process::Command::new(&installer_path)
        .spawn()
        .map_err(|e| format!("Failed to launch Ollama installer: {e}"))?;

    Ok("Установщик Ollama успешно запущен".to_string())
}

#[tauri::command]
async fn start_fastapi_sidecar(
    app: AppHandle,
    state: State<'_, BackendProcess>,
) -> Result<BackendStatus, String> {
    {
        let child = state
            .child
            .lock()
            .map_err(|_| "backend state lock poisoned".to_string())?;
        if child.is_some() {
            return health_status().await;
        }
    }

    let sidecar = app
        .shell()
        .sidecar("asterion-backend")
        .map_err(|error| format!("failed to prepare backend sidecar: {error}"))?
        .args([
            "--host",
            BACKEND_HOST,
            "--port",
            "8000",
        ]);

    let (mut rx, child) = sidecar
        .spawn()
        .map_err(|error| format!("failed to spawn backend sidecar: {error}"))?;

    {
        let mut slot = state
            .child
            .lock()
            .map_err(|_| "backend state lock poisoned".to_string())?;
        *slot = Some(child);
    }

    let events_app = app.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes).to_string();
                    let _ = events_app.emit("asterion-backend-stdout", line);
                }
                CommandEvent::Stderr(bytes) => {
                    let line = String::from_utf8_lossy(&bytes).to_string();
                    let _ = events_app.emit("asterion-backend-stderr", line);
                }
                CommandEvent::Terminated(payload) => {
                    let _ = events_app.emit("asterion-backend-terminated", format!("{payload:?}"));
                }
                _ => {}
            }
        }
    });

    wait_for_health(Duration::from_secs(5)).await
}

#[tauri::command]
async fn fastapi_health_check() -> Result<BackendStatus, String> {
    health_status().await
}

#[tauri::command]
async fn shutdown_fastapi_sidecar(
    state: State<'_, BackendProcess>,
) -> Result<BackendStatus, String> {
    let maybe_child = {
        let mut child = state
            .child
            .lock()
            .map_err(|_| "backend state lock poisoned".to_string())?;
        child.take()
    };

    if let Some(mut child) = maybe_child {
        child
            .kill()
            .map_err(|error| format!("failed to kill backend sidecar: {error}"))?;
    }

    Ok(BackendStatus {
        running: false,
        host: BACKEND_HOST.to_string(),
        port: BACKEND_PORT,
        health: serde_json::json!({"status": "stopped"}),
    })
}

async fn wait_for_health(timeout: Duration) -> Result<BackendStatus, String> {
    let started = std::time::Instant::now();
    while started.elapsed() < timeout {
        if let Ok(status) = health_status().await {
            return Ok(status);
        }
        tokio::time::sleep(Duration::from_millis(100)).await;
    }
    Err("backend sidecar did not become healthy within 5 seconds".to_string())
}

async fn health_status() -> Result<BackendStatus, String> {
    let url = format!("http://{BACKEND_HOST}:{BACKEND_PORT}/api/health");
    let health = reqwest::Client::new()
        .get(url)
        .timeout(Duration::from_secs(1))
        .send()
        .await
        .map_err(|error| format!("backend health request failed: {error}"))?
        .error_for_status()
        .map_err(|error| format!("backend health returned error: {error}"))?
        .json::<serde_json::Value>()
        .await
        .map_err(|error| format!("backend health payload was invalid: {error}"))?;

    Ok(BackendStatus {
        running: true,
        host: BACKEND_HOST.to_string(),
        port: BACKEND_PORT,
        health,
    })
}

fn setup_tray(app: &tauri::App) -> Result<(), tauri::Error> {
    let show = MenuItem::with_id(app, "show", "Показать окно", true, None::<&str>)?;
    let restart = MenuItem::with_id(app, "restart", "Перезапустить sidecar", true, None::<&str>)?;
    let exit = MenuItem::with_id(app, "exit", "Выход", true, None::<&str>)?;

    let menu = Menu::with_items(app, &[&show, &restart, &exit])?;

    let icon = app.default_window_icon()
        .cloned()
        .unwrap_or_else(|| {
            tauri::image::Image::from_bytes(&[0; 4]).unwrap()
        });

    let _tray = TrayIconBuilder::new()
        .icon(icon)
        .menu(&menu)
        .on_menu_event(|app, event| {
            match event.id.as_ref() {
                "show" => {
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.focus();
                    }
                }
                "restart" => {
                    let app_clone = app.clone();
                    tauri::async_runtime::spawn(async move {
                        let state = app_clone.state::<BackendProcess>();
                        let _ = shutdown_fastapi_sidecar(state.clone()).await;
                        let _ = start_fastapi_sidecar(app_clone, state).await;
                    });
                }
                "exit" => {
                    app.exit(0);
                }
                _ => {}
            }
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click { .. } = event {
                let app = tray.app_handle();
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.focus();
                }
            }
        })
        .build(app)?;

    Ok(())
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .manage(BackendProcess::default())
        .invoke_handler(tauri::generate_handler![
            start_fastapi_sidecar,
            fastapi_health_check,
            shutdown_fastapi_sidecar,
            get_gpu_info,
            pick_rag_file,
            install_ollama
        ])
        .setup(|app| {
            let app_handle = app.handle().clone();
            let state = app_handle.state::<BackendProcess>();
            tauri::async_runtime::spawn(async move {
                let start_res = start_fastapi_sidecar(app_handle.clone(), state).await;
                if let Some(splash) = app_handle.get_webview_window("splashscreen") {
                    let _ = splash.close();
                }
                if let Some(main) = app_handle.get_webview_window("main") {
                    let _ = main.show();
                    let _ = main.focus();
                }
                if let Err(err) = start_res {
                    eprintln!("Failed to start sidecar: {err}");
                }
            });

            setup_tray(app)?;

            let shortcut = Shortcut::new(Some(Modifiers::CONTROL | Modifiers::SHIFT), Code::Space);
            app.global_shortcut().on_shortcut(shortcut, |app, _shortcut, event| {
                if event.state() == ShortcutState::Pressed {
                    if let Some(window) = app.get_webview_window("main") {
                        if window.is_visible().unwrap_or(false) {
                            let _ = window.hide();
                        } else {
                            let _ = window.show();
                            let _ = window.focus();
                        }
                    }
                }
            })?;

            let args: Vec<String> = std::env::args().collect();
            for arg in args {
                if arg.starts_with("asterion://") {
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.emit("deeplink-received", arg);
                    }
                }
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Asterion AI desktop shell");
}
