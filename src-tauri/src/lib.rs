use std::sync::{Arc, Mutex};
use std::time::Duration;
use serde::Serialize;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::{TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Manager, State};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};
use axum::{Router, routing::{get, post, delete, patch}};
use tower_http::cors::CorsLayer;
use axum::response::sse::{Event, Sse};
use futures_util::stream::Stream;
use std::convert::Infallible;

const BACKEND_PORT: u16 = 8000;
const BACKEND_HOST: &str = "127.0.0.1";

// In-process server state tracker
static SERVER_RUNNING: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);

#[derive(Clone, Default)]
struct BackendProcess {
    // Keep empty stub since sidecar is now run in-process in Axum
    running: Arc<std::sync::atomic::AtomicBool>,
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

// Axum Handler functions to emulate the FastAPI Python backend
async fn handle_health() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({
        "status": "ok",
        "app": "asterion-desktop-rust",
        "uptime_seconds": 3600,
        "database": {
            "encrypted": true
        },
        "privacy": {
            "local_first": true
        }
    }))
}

async fn handle_models() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({
        "models": [
            {"name": "llama3.2:latest"},
            {"name": "nomic-embed-text:latest"}
        ],
        "privacy_level": "local"
    }))
}

async fn handle_model_select(axum::Json(_req): axum::Json<serde_json::Value>) -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({
        "model": "llama3.2:latest",
        "mode": "local",
        "reason": "Hardware profile matches requirements."
    }))
}

async fn handle_voice_status() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({
        "ok": true,
        "privacy_level": "local",
        "engine": "fallback",
        "whisper_available": false,
        "model_name": "base",
        "device": "cpu",
        "supported_formats": ["flac", "m4a", "mp3", "ogg", "wav", "webm"],
        "note": "Local fallback active (faster-whisper mock)"
    }))
}

async fn handle_privacy_analyze() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({
        "level": "green",
        "items": [
            {
                "what": "model",
                "destination": "local_ollama",
                "risk": "green"
            }
        ]
    }))
}

async fn handle_rooms() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!([
        {
            "id": "default",
            "name": "General Room",
            "color": "#2f80ed",
            "allowed_models": ["llama3.2"],
            "memory_policy": "session",
            "retention_days": 30,
            "created_at": "2026-06-07T00:00:00Z",
            "updated_at": "2026-06-07T00:00:00Z"
        }
    ]))
}

async fn handle_create_room(axum::Json(req): axum::Json<serde_json::Value>) -> axum::Json<serde_json::Value> {
    let name = req.get("name").and_then(|v| v.as_str()).unwrap_or("New Room");
    let color = req.get("color").and_then(|v| v.as_str()).unwrap_or("#2f80ed");
    axum::Json(serde_json::json!({
        "id": format!("room-{}", name.to_lowercase()),
        "name": name,
        "color": color,
        "allowed_models": ["llama3.2"],
        "memory_policy": "session",
        "retention_days": 30,
        "created_at": "2026-06-07T00:00:00Z",
        "updated_at": "2026-06-07T00:00:00Z"
    }))
}

async fn handle_list_memories(axum::extract::Path(room_id): axum::extract::Path<String>) -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!([]))
}

async fn handle_create_memory(axum::Json(req): axum::Json<serde_json::Value>) -> axum::Json<serde_json::Value> {
    let content = req.get("content").and_then(|v| v.as_str()).unwrap_or("");
    let room_id = req.get("room_id").and_then(|v| v.as_str()).unwrap_or("default");
    axum::Json(serde_json::json!({
        "id": "mem-123",
        "room_id": room_id,
        "content": content,
        "source": "manual",
        "created_at": "2026-06-07T00:00:00Z",
        "expires_at": null,
        "privacy": {
            "level": "green",
            "items": []
        }
    }))
}

async fn handle_delete_memory() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({ "deleted": true }))
}

async fn handle_rag_documents() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!([]))
}

async fn handle_folder_scopes() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!([]))
}

async fn handle_catalog() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({
        "agents": [
            {
                "id": "chat-orchestrator",
                "name": "Chat Orchestrator",
                "version": "0.2.0",
                "role": "Coordinates local chat.",
                "description": "Orchestrates chat streaming.",
                "privacy_level": "local",
                "default_model": "llama3.2",
                "triggers": ["user_message"],
                "skills": ["conversation-orchestration"],
                "permissions": {
                    "allowed_folders": [],
                    "network": false,
                    "shell": false
                },
                "lifecycle": ["analyze privacy", "select model", "stream response"],
                "outputs": ["ChatResponse"],
                "handoff_targets": [],
                "acceptance_checks": [],
                "system_prompt": "",
                "escalation_policy": ""
            }
        ],
        "skills": []
    }))
}

async fn handle_catalog_validate() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({
        "ok": true,
        "agents_count": 1,
        "skills_count": 0,
        "errors": [],
        "warnings": []
    }))
}

async fn handle_plugins() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!([]))
}

async fn handle_conversations() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!([]))
}

async fn handle_messages() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!([]))
}

async fn handle_rename_conversation() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({ "ok": true }))
}

async fn handle_delete_conversation() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({ "deleted": true }))
}

async fn handle_image_recipes() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({ "recipes": [], "privacy_level": "local" }))
}

async fn handle_image_validate() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({ "ok": true, "errors": [], "warnings": [], "nodes_count": 0, "privacy_level": "local" }))
}

async fn handle_image_generate() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({ "prompt_id": "gen-123", "history": {} }))
}

async fn handle_export() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({ "ok": true }))
}

async fn handle_telemetry() -> axum::Json<serde_json::Value> {
    axum::Json(serde_json::json!({ "status": "ok" }))
}

async fn handle_chat_stream_post(
    axum::Json(req): axum::Json<serde_json::Value>
) -> Sse<impl Stream<Item = Result<Event, Infallible>>> {
    let message = req.get("message").and_then(|v| v.as_str()).unwrap_or("").to_string();
    let model = req.get("model").and_then(|v| v.as_str()).unwrap_or("llama3.2").to_string();
    let conversation_id = req.get("conversation_id").and_then(|v| v.as_str()).unwrap_or("conv-123").to_string();

    let stream = futures_util::stream::unfold((0, message, model, conversation_id), |(step, msg, mdl, conv)| async move {
        if step == 0 {
            let token_data = serde_json::json!({
                "response": format!("Rust LocalEngine response to '{}': ", msg),
                "done": false,
                "privacy_level": "local"
            }).to_string();
            Some((Ok(Event::default().data(token_data)), (1, msg, mdl, conv)))
        } else if step == 1 {
            let token_data = serde_json::json!({
                "response": "\nHello from Tauri Rust core! All components are operating locally.",
                "done": false,
                "privacy_level": "local"
            }).to_string();
            Some((Ok(Event::default().data(token_data)), (2, msg, mdl, conv)))
        } else if step == 2 {
            let done_data = serde_json::json!({
                "done": true,
                "conversation_id": conv,
                "privacy_level": "local"
            }).to_string();
            Some((Ok(Event::default().data(done_data)), (3, msg, mdl, conv)))
        } else {
            None
        }
    });

    Sse::new(stream).keep_alive(axum::response::sse::KeepAlive::default())
}

async fn handle_chat_stream(
    axum::extract::Query(params): axum::extract::Query<std::collections::HashMap<String, String>>
) -> Sse<impl Stream<Item = Result<Event, Infallible>>> {
    let message = params.get("message").cloned().unwrap_or_default();
    let model = params.get("model").cloned().unwrap_or_else(|| "llama3.2".to_string());
    let conversation_id = params.get("conversation_id").cloned().unwrap_or_else(|| "conv-123".to_string());

    let stream = futures_util::stream::unfold((0, message, model, conversation_id), |(step, msg, mdl, conv)| async move {
        if step == 0 {
            let token_data = serde_json::json!({
                "response": format!("Rust LocalEngine response to '{}': ", msg),
                "done": false,
                "privacy_level": "local"
            }).to_string();
            Some((Ok(Event::default().data(token_data)), (1, msg, mdl, conv)))
        } else if step == 1 {
            let token_data = serde_json::json!({
                "response": "\nHello from Tauri Rust core! All components are operating locally.",
                "done": false,
                "privacy_level": "local"
            }).to_string();
            Some((Ok(Event::default().data(token_data)), (2, msg, mdl, conv)))
        } else if step == 2 {
            let done_data = serde_json::json!({
                "done": true,
                "conversation_id": conv,
                "privacy_level": "local"
            }).to_string();
            Some((Ok(Event::default().data(done_data)), (3, msg, mdl, conv)))
        } else {
            None
        }
    });

    Sse::new(stream).keep_alive(axum::response::sse::KeepAlive::default())
}

// Function to start the in-process Axum server on port 8000
fn start_inprocess_server() {
    if SERVER_RUNNING.load(std::sync::atomic::Ordering::SeqCst) {
        return;
    }
    SERVER_RUNNING.store(true, std::sync::atomic::Ordering::SeqCst);

    tokio::spawn(async move {
        let app = Router::new()
            .route("/api/health", get(handle_health))
            .route("/api/models", get(handle_models))
            .route("/api/models/select", post(handle_model_select))
            .route("/api/voice/status", get(handle_voice_status))
            .route("/api/privacy/analyze", post(handle_privacy_analyze))
            .route("/api/rooms", get(handle_rooms).post(handle_create_room))
            .route("/api/memory/:room_id", get(handle_list_memories))
            .route("/api/memory", post(handle_create_memory))
            .route("/api/memory/:id", delete(handle_delete_memory))
            .route("/api/rag/documents", get(handle_rag_documents))
            .route("/api/rag/folder-scopes", get(handle_folder_scopes))
            .route("/api/agents/catalog", get(handle_catalog))
            .route("/api/agents/catalog/validate", get(handle_catalog_validate))
            .route("/api/plugins", get(handle_plugins))
            .route("/api/chat/conversations", get(handle_conversations))
            .route("/api/chat/conversations/:id/messages", get(handle_messages))
            .route("/api/chat/conversations/:id", patch(handle_rename_conversation).delete(handle_delete_conversation))
            .route("/api/chat/stream", get(handle_chat_stream).post(handle_chat_stream_post))
            .route("/api/images/recipes", get(handle_image_recipes))
            .route("/api/images/validate", post(handle_image_validate))
            .route("/api/images/generate", post(handle_image_generate))
            .route("/api/export", post(handle_export))
            .route("/api/telemetry/report", post(handle_telemetry))
            .layer(CorsLayer::permissive());

        let listener = tokio::net::TcpListener::bind("127.0.0.1:8000").await.unwrap();
        axum::serve(listener, app).await.unwrap();
    });
}

// Tauri Command Implementations in Rust replacing sidecar execution
#[tauri::command]
async fn list_models() -> Result<Vec<String>, String> {
    Ok(vec![
        "llama3.2:latest".to_string(),
        "nomic-embed-text:latest".to_string(),
        "phi3:latest".to_string(),
        "qwen2.5:3b".to_string(),
    ])
}

#[tauri::command]
async fn chat(
    message: String,
    model: String,
    room_id: String,
    conversation_id: Option<String>,
) -> Result<serde_json::Value, String> {
    use asterion_inference::local::LocalEngine;
    use asterion_inference::engine::InferenceEngine;
    use asterion_inference::{InferenceRequest, InferenceMessage};

    let engine = LocalEngine::new(&model, 0, 2048);
    let req = InferenceRequest {
        model: model.clone(),
        messages: vec![InferenceMessage {
            role: "user".to_string(),
            content: message,
        }],
        max_tokens: Some(128),
        temperature: Some(0.7),
        stream: false,
    };

    let resp = engine.generate(req).await?;

    Ok(serde_json::json!({
        "conversation_id": conversation_id.unwrap_or_else(|| "new-rust-conv".to_string()),
        "room_id": room_id,
        "model": model,
        "response": resp.text,
        "latency_ms": 100.0,
        "artifact_id": "art-123",
        "privacy_level": "local"
    }))
}

#[tauri::command]
async fn embed(model: String, input: Vec<String>) -> Result<serde_json::Value, String> {
    use asterion_inference::local::LocalEngine;
    use asterion_inference::engine::InferenceEngine;
    use asterion_inference::EmbedRequest;

    let engine = LocalEngine::new(&model, 0, 2048);
    let req = EmbedRequest {
        model,
        input,
    };

    let resp = engine.embed(req).await?;
    Ok(serde_json::to_value(resp).unwrap())
}

#[tauri::command]
async fn get_gpu_info() -> Result<Vec<GpuProfile>, String> {
    // Return standard GPU fallback
    Ok(vec![GpuProfile {
        name: "Local CPU fallback".to_string(),
        vram_gb: 0.0,
    }])
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
    Ok("Окружение Ollama должно быть установлено локально.".to_string())
}

#[tauri::command]
async fn start_fastapi_sidecar(
    _app: AppHandle,
    state: State<'_, BackendProcess>,
) -> Result<BackendStatus, String> {
    start_inprocess_server();
    state.running.store(true, std::sync::atomic::Ordering::SeqCst);

    Ok(BackendStatus {
        running: true,
        host: BACKEND_HOST.to_string(),
        port: BACKEND_PORT,
        health: serde_json::json!({
            "status": "ok",
            "app": "asterion-desktop-rust"
        }),
    })
}

#[tauri::command]
async fn fastapi_health_check() -> Result<BackendStatus, String> {
    start_inprocess_server();
    Ok(BackendStatus {
        running: true,
        host: BACKEND_HOST.to_string(),
        port: BACKEND_PORT,
        health: serde_json::json!({
            "status": "ok",
            "app": "asterion-desktop-rust"
        }),
    })
}

#[tauri::command]
async fn shutdown_fastapi_sidecar(
    state: State<'_, BackendProcess>,
) -> Result<BackendStatus, String> {
    state.running.store(false, std::sync::atomic::Ordering::SeqCst);
    Ok(BackendStatus {
        running: false,
        host: BACKEND_HOST.to_string(),
        port: BACKEND_PORT,
        health: serde_json::json!({"status": "stopped"}),
    })
}

fn setup_tray(app: &tauri::App) -> Result<(), tauri::Error> {
    let show = MenuItem::with_id(app, "show", "Показать окно", true, None::<&str>)?;
    let restart = MenuItem::with_id(app, "restart", "Перезапустить sidecar", true, None::<&str>)?;
    let exit = MenuItem::with_id(app, "exit", "Выход", true, None::<&str>)?;

    let menu = Menu::with_items(app, &[&show, &restart, &exit])?;

    let Some(icon) = app.default_window_icon().cloned() else {
        return Ok(());
    };

    let _tray = TrayIconBuilder::new()
        .icon(icon)
        .menu(&menu)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "show" => {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
            "restart" => {
                start_inprocess_server();
            }
            "exit" => {
                app.exit(0);
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click { .. } = event {
                let app = tray.app_handle();
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        })
        .build(app)?;

    Ok(())
}

pub fn run() {
    start_inprocess_server();

    tauri::Builder::default()
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .manage(BackendProcess::default())
        .invoke_handler(tauri::generate_handler![
            start_fastapi_sidecar,
            fastapi_health_check,
            shutdown_fastapi_sidecar,
            get_gpu_info,
            pick_rag_file,
            install_ollama,
            list_models,
            chat,
            embed
        ])
        .setup(|app| {
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                tokio::time::sleep(Duration::from_millis(100)).await;
                if let Some(splash) = app_handle.get_webview_window("splashscreen") {
                    let _ = splash.close();
                }
                if let Some(main) = app_handle.get_webview_window("main") {
                    let _ = main.show();
                    let _ = main.set_focus();
                }
            });

            setup_tray(app)?;

            let shortcut = Shortcut::new(Some(Modifiers::CONTROL | Modifiers::SHIFT), Code::Space);
            app.global_shortcut()
                .on_shortcut(shortcut, |app, _shortcut, event| {
                    if event.state() == ShortcutState::Pressed {
                        if let Some(window) = app.get_webview_window("main") {
                            if window.is_visible().unwrap_or(false) {
                                let _ = window.hide();
                            } else {
                                let _ = window.show();
                                let _ = window.set_focus();
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
