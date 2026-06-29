/**
 * Cliente do sidecar Python (FastAPI rodando em localhost).
 *
 * O Tauri sobe o sidecar e expõe a porta; aqui apenas conversamos com ele via
 * HTTP. Tudo permanece em 127.0.0.1 — nenhuma requisição sai da máquina.
 */

const DEFAULT_PORT = 8756;

let cachedPort: number | null = null;

/** Pergunta ao Rust a porta do sidecar (com fallback ao padrão). */
async function resolvePort(): Promise<number> {
  if (cachedPort !== null) return cachedPort;
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    cachedPort = await invoke<number>("sidecar_port");
  } catch {
    cachedPort = DEFAULT_PORT;
  }
  return cachedPort;
}

async function baseUrl(): Promise<string> {
  const port = await resolvePort();
  return `http://127.0.0.1:${port}`;
}

export interface HealthResponse {
  status: string;
  version: string;
  python: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = await baseUrl();
  const res = await fetch(`${url}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`Sidecar ${path} respondeu ${res.status}`);
  }
  return res.json() as Promise<T>;
}

/** Verifica se o sidecar está no ar. */
export function health(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

/**
 * Aguarda o sidecar ficar disponível (usado na inicialização do app).
 * Faz polling até `timeoutMs`.
 */
export async function waitForSidecar(timeoutMs = 30_000): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      await health();
      return true;
    } catch {
      await new Promise((r) => setTimeout(r, 500));
    }
  }
  return false;
}
