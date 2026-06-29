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

/** Erro de requisição ao sidecar, carregando status e detalhe do servidor. */
export class SidecarError extends Error {
  constructor(
    public status: number,
    public detail: string,
    path: string,
  ) {
    super(`Sidecar ${path} respondeu ${status}: ${detail}`);
    this.name = "SidecarError";
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
}

/** Faz a requisição e lança `SidecarError` (com o detalhe do servidor) se !ok. */
async function fetchOrThrow(path: string, init?: RequestInit): Promise<Response> {
  const url = await baseUrl();
  const res = await fetch(`${url}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      if (data && typeof data.detail === "string") detail = data.detail;
    } catch {
      /* corpo não-JSON: mantém statusText */
    }
    throw new SidecarError(res.status, detail, path);
  }
  return res;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await fetchOrThrow(path, {
    method: opts.method ?? "GET",
    headers: { "Content-Type": "application/json" },
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// --- Health -------------------------------------------------------------

export interface HealthResponse {
  status: string;
  version: string;
  python: string;
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

// --- Tipos de domínio ---------------------------------------------------

export interface Project {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Audio {
  id: number;
  project_id: number;
  path: string;
  filename: string;
  duration: number | null;
  language: string | null;
  model: string | null;
  device: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Word {
  start: number;
  end: number;
  word: string;
  probability: number | null;
}

export interface Segment {
  id: number;
  audio_id: number;
  seq: number;
  start: number;
  end: number;
  text: string;
  speaker: string | null;
  words: Word[];
}

export interface Code {
  id: number;
  project_id: number;
  name: string;
  color: string | null;
  created_at: string;
}

/** Código atribuído a um trecho (com memo opcional do vínculo). */
export interface AssignedCode {
  id: number;
  name: string;
  color: string | null;
  memo: string | null;
}

/** Mapa segment_id (string) -> códigos atribuídos. */
export type CodingMap = Record<string, AssignedCode[]>;

export interface CodeFrequency {
  id: number;
  name: string;
  color: string | null;
  segment_count: number;
  word_count: number;
}

export interface CodeCooccurrence {
  code_a: number;
  code_b: number;
  name_a: string;
  name_b: string;
  count: number;
}

export interface QualitativeSummary {
  codes: CodeFrequency[];
  cooccurrence: CodeCooccurrence[];
  coded_segments: number;
  total_segments: number;
  coverage: number;
}

export interface TermFrequency {
  term: string;
  count: number;
}

/** Recorte por falante (presente só quando há diarização). */
export interface SpeakerMetrics {
  speaker: string | null;
  word_count: number;
  spoken_seconds: number;
  speaking_rate: number;
}

/** Métricas quantitativas de um áudio transcrito. */
export interface AudioMetrics {
  word_count: number;
  unique_words: number;
  spoken_seconds: number;
  speaking_rate: number;
  lexical_richness: number;
  top_terms: TermFrequency[];
  speakers: SpeakerMetrics[];
}

/** Métricas quantitativas de um áudio dentro do agregado do projeto. */
export interface ProjectAudioMetrics {
  audio_id: number;
  filename: string;
  word_count: number;
  unique_words: number;
  spoken_seconds: number;
  speaking_rate: number;
  lexical_richness: number;
}

/** Métricas quantitativas agregadas do projeto, com recorte por áudio. */
export interface QuantitativeSummary {
  word_count: number;
  unique_words: number;
  spoken_seconds: number;
  speaking_rate: number;
  lexical_richness: number;
  top_terms: TermFrequency[];
  audios: ProjectAudioMetrics[];
}

/** Rótulo de sentimento de um trecho. */
export type SentimentLabel = "positive" | "negative" | "neutral";

/** Contagem de trechos por sentimento. */
export interface SentimentDistribution {
  positive: number;
  negative: number;
  neutral: number;
}

/** Distribuição de sentimento de um áudio dentro do agregado do projeto. */
export interface SentimentByAudio {
  audio_id: number;
  filename: string;
  distribution: SentimentDistribution;
  /** Polaridade média P(pos) − P(neg) em [-1, 1]. */
  avg_polarity: number;
}

/** Um trecho na linha do tempo de sentimento. */
export interface SentimentPoint {
  segment_id: number;
  audio_id: number;
  start: number;
  label: SentimentLabel;
  /** Polaridade do trecho P(pos) − P(neg) em [-1, 1]. */
  polarity: number;
  text: string;
}

/** Resumo de sentimento do projeto, com recorte por áudio e linha do tempo. */
export interface SentimentSummary {
  total_segments: number;
  distribution: SentimentDistribution;
  /** Polaridade média do projeto em [-1, 1]. */
  avg_polarity: number;
  audios: SentimentByAudio[];
  timeline: SentimentPoint[];
}

// --- Projetos -----------------------------------------------------------

export const projects = {
  list: () => request<Project[]>("/projects"),
  get: (id: number) => request<Project>(`/projects/${id}`),
  create: (name: string, description?: string) =>
    request<Project>("/projects", {
      method: "POST",
      body: { name, description },
    }),
  update: (id: number, patch: { name?: string; description?: string }) =>
    request<Project>(`/projects/${id}`, { method: "PATCH", body: patch }),
  remove: (id: number) =>
    request<void>(`/projects/${id}`, { method: "DELETE" }),
};

// --- Áudios -------------------------------------------------------------

export interface NewAudio {
  path: string;
  filename: string;
  duration?: number;
  language?: string;
  model?: string;
  device?: string;
}

export const audios = {
  list: (projectId: number) =>
    request<Audio[]>(`/projects/${projectId}/audios`),
  get: (id: number) => request<Audio>(`/audios/${id}`),
  create: (projectId: number, audio: NewAudio) =>
    request<Audio>(`/projects/${projectId}/audios`, {
      method: "POST",
      body: audio,
    }),
  remove: (id: number) => request<void>(`/audios/${id}`, { method: "DELETE" }),
  segments: (id: number) => request<Segment[]>(`/audios/${id}/segments`),
  coding: (id: number) => request<CodingMap>(`/audios/${id}/coding`),
};

// --- Códigos / codificação qualitativa ----------------------------------

export const codes = {
  list: (projectId: number) =>
    request<Code[]>(`/projects/${projectId}/codes`),
  create: (projectId: number, name: string, color?: string) =>
    request<Code>(`/projects/${projectId}/codes`, {
      method: "POST",
      body: { name, color },
    }),
  remove: (id: number) => request<void>(`/codes/${id}`, { method: "DELETE" }),
  assign: (segmentId: number, codeId: number, memo?: string) =>
    request<void>("/codes/assign", {
      method: "POST",
      body: { segment_id: segmentId, code_id: codeId, memo },
    }),
  unassign: (segmentId: number, codeId: number) =>
    request<void>("/codes/unassign", {
      method: "POST",
      body: { segment_id: segmentId, code_id: codeId },
    }),
  segments: (codeId: number) =>
    request<Segment[]>(`/codes/${codeId}/segments`),
  forSegment: (segmentId: number) =>
    request<AssignedCode[]>(`/segments/${segmentId}/codes`),
};

// --- Análise ------------------------------------------------------------

export const analysis = {
  qualitative: (projectId: number) =>
    request<QualitativeSummary>(`/projects/${projectId}/analysis/qualitative`),
  quantitative: (projectId: number) =>
    request<QuantitativeSummary>(
      `/projects/${projectId}/analysis/quantitative`,
    ),
  quantitativeAudio: (audioId: number) =>
    request<AudioMetrics>(`/audios/${audioId}/analysis/quantitative`),
  sentiment: (projectId: number, refresh = false) =>
    request<SentimentSummary>(
      `/projects/${projectId}/analysis/sentiment${refresh ? "?refresh=true" : ""}`,
    ),
};

// --- Exportação ---------------------------------------------------------

/**
 * Fonte única dos formatos de transcrição: o conjunto de formatos, sua família
 * (rótulo na UI) e se carregam a codificação qualitativa. Tudo o mais — o tipo
 * `TranscriptFormat`, as opções do menu e a decisão de incluir codificação —
 * deriva daqui, então adicionar um formato é uma linha só.
 */
export const TRANSCRIPT_FORMATS = [
  { fmt: "csv", kind: "table", supportsCoding: true },
  { fmt: "tsv", kind: "table", supportsCoding: true },
  { fmt: "json", kind: "data", supportsCoding: true },
  { fmt: "srt", kind: "subtitle", supportsCoding: false },
  { fmt: "vtt", kind: "subtitle", supportsCoding: false },
  { fmt: "docx", kind: "document", supportsCoding: true },
  { fmt: "pdf", kind: "document", supportsCoding: true },
] as const satisfies readonly {
  fmt: string;
  kind: "table" | "data" | "subtitle" | "document";
  supportsCoding: boolean;
}[];

/** Formatos de exportação de transcrição (derivado de `TRANSCRIPT_FORMATS`). */
export type TranscriptFormat = (typeof TRANSCRIPT_FORMATS)[number]["fmt"];

/** Formatos de exportação de resultado de análise. */
export type AnalysisExportFormat = "csv" | "tsv" | "json";

/** Análises exportáveis. */
export type AnalysisKind = "quantitative" | "sentiment";

/**
 * Baixa os bytes de uma exportação do sidecar, abre o diálogo "Salvar como" e
 * grava no caminho escolhido. Devolve o caminho salvo, ou `null` se o usuário
 * cancelar. O sidecar é a fonte dos bytes; o frontend só escolhe onde gravar.
 */
async function downloadExport(
  path: string,
  suggestedName: string,
  ext: string,
): Promise<string | null> {
  const res = await fetchOrThrow(path);
  const bytes = new Uint8Array(await res.arrayBuffer());

  const { save } = await import("@tauri-apps/plugin-dialog");
  const target = await save({
    defaultPath: suggestedName,
    filters: [{ name: ext.toUpperCase(), extensions: [ext] }],
  });
  if (!target) return null; // usuário cancelou

  const { writeFile } = await import("@tauri-apps/plugin-fs");
  await writeFile(target, bytes);
  return target;
}

export const exports = {
  /** Exporta a transcrição de um áudio. */
  audioTranscript: (
    audioId: number,
    fmt: TranscriptFormat,
    { coding = false }: { coding?: boolean } = {},
  ) =>
    downloadExport(
      `/audios/${audioId}/export/${fmt}${coding ? "?coding=true" : ""}`,
      `transcricao.${fmt}`,
      fmt,
    ),

  /** Exporta a transcrição de todos os áudios do projeto. */
  projectTranscript: (
    projectId: number,
    fmt: TranscriptFormat,
    { coding = false }: { coding?: boolean } = {},
  ) =>
    downloadExport(
      `/projects/${projectId}/export/${fmt}${coding ? "?coding=true" : ""}`,
      `transcricao.${fmt}`,
      fmt,
    ),

  /** Exporta o resultado de uma análise do projeto. */
  analysis: (
    projectId: number,
    kind: AnalysisKind,
    fmt: AnalysisExportFormat,
  ) =>
    downloadExport(
      `/projects/${projectId}/analysis/${kind}/export/${fmt}`,
      `${kind}.${fmt}`,
      fmt,
    ),
};

// --- Transcrição --------------------------------------------------------

export interface TranscribeRequest {
  audio_path: string;
  language?: string | null;
  model?: string | null;
  device?: string;
  /** Se informado, o sidecar persiste o resultado nesse áudio. */
  audio_id?: number;
}

export interface TranscribeResponse {
  language: string;
  language_probability: number;
  duration: number;
  model: string;
  device: string;
  segments: Segment[];
}

/** Dispara a transcrição (síncrona por ora). */
export function transcribe(
  req: TranscribeRequest,
): Promise<TranscribeResponse> {
  return request<TranscribeResponse>("/transcribe", {
    method: "POST",
    body: req,
  });
}
