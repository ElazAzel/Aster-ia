declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown;
  }
}

export type BackendStatus = {
  running: boolean;
  host: string;
  port: number;
  health: unknown;
};

export function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && window.__TAURI_INTERNALS__ !== undefined;
}

async function invokeBackend(command: string): Promise<BackendStatus> {
  if (!isTauriRuntime()) {
    throw new Error('Tauri runtime is unavailable in browser mode.');
  }

  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<BackendStatus>(command);
}

export function startFastapiSidecar(): Promise<BackendStatus> {
  return invokeBackend('start_fastapi_sidecar');
}

export function fastapiHealthCheck(): Promise<BackendStatus> {
  return invokeBackend('fastapi_health_check');
}

export function shutdownFastapiSidecar(): Promise<BackendStatus> {
  return invokeBackend('shutdown_fastapi_sidecar');
}
