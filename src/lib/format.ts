/** Utilitários de formatação compartilhados pela UI. */

/**
 * Formata segundos como tempo legível: `mm:ss` (ou `h:mm:ss` quando passa de 1h).
 * Usado nos timestamps dos segmentos da transcrição.
 */
export function formatTime(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(s).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

/** Duração aproximada legível, ex.: "12 min", "1 h 05 min", "45 s". */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  const total = Math.floor(seconds);
  if (total < 60) return `${total} s`;
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  if (h > 0) return `${h} h ${String(m).padStart(2, "0")} min`;
  return `${m} min`;
}

/** Extrai uma mensagem legível de um erro desconhecido (catch). */
export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

/** Substitui `{chave}` por valores — interpolação simples para strings i18n. */
export function interpolate(
  template: string,
  vars: Record<string, string | number>,
): string {
  return template.replace(/\{(\w+)\}/g, (_, key) =>
    key in vars ? String(vars[key]) : `{${key}}`,
  );
}
