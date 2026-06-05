use std::sync::Mutex;
use std::time::Duration;

use serde::Serialize;
use tauri::{AppHandle, Emitter, State};
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

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess::default())
        .invoke_handler(tauri::generate_handler![
            start_fastapi_sidecar,
            fastapi_health_check,
            shutdown_fastapi_sidecar
        ])
        .run(tauri::generate_context!())
        .expect("error while running Asterion AI desktop shell");
}
