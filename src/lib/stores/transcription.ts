/**
 * Estado global das transcrições em andamento.
 *
 * Vive no escopo do módulo (como `sidecar/status.ts`), fora de qualquer
 * componente, para dois fins que se resolvem juntos:
 *
 *  1. Trava por-arquivo: enquanto um áudio está no mapa, disparar de novo é
 *     ignorado — torna impossível a dupla transcrição do MESMO arquivo, em
 *     qualquer aba (outros arquivos seguem livres).
 *  2. Continuidade entre abas: a promessa da transcrição e a fração de progresso
 *     moram aqui, não no componente. Ao sair de /transcription (que desmonta a
 *     página) a transcrição não é interrompida, e ao voltar a UI relê o estado.
 *
 * A persistência do RESULTADO é do servidor (o sidecar grava via `audio_id`);
 * este store cuida só do efêmero: "quais estão rodando" e "qual a fração".
 */
import { writable, get } from "svelte/store";
import { transcribe, type Audio, type TranscribeResponse } from "$lib/sidecar/client";

/** Estado de um áudio em transcrição. `fraction=null` = ainda preparando o modelo. */
export interface TranscriptionState {
  fraction: number | null;
}

/** Mapa audio_id -> estado. Reatribuído a cada mudança (imutável) p/ os stores. */
export const activeTranscriptions = writable<Map<number, TranscriptionState>>(
  new Map(),
);

/** Opções do motor (modelo/dispositivo), vindas das configurações. */
export interface TranscriptionOptions {
  model?: string | null;
  device?: string;
}

/** Callbacks para a UI reconciliar seu estado local ao fim da transcrição. */
export interface TranscriptionCallbacks {
  onDone?: (result: TranscribeResponse) => void;
  onError?: (message: string) => void;
}

/** True se aquele áudio está transcrevendo agora (para travar o botão). */
export function isTranscribing(audioId: number): boolean {
  return get(activeTranscriptions).has(audioId);
}

function patch(audioId: number, state: TranscriptionState | null) {
  activeTranscriptions.update((map) => {
    const next = new Map(map);
    if (state === null) next.delete(audioId);
    else next.set(audioId, state);
    return next;
  });
}

/**
 * Dispara a transcrição de `audio` uma única vez.
 *
 * Se o áudio já está em andamento, retorna imediatamente (guarda contra dupla
 * transcrição). Caso contrário registra o áudio no mapa, transmite o progresso
 * (fração) e, ao terminar, remove-o do mapa e chama o callback correspondente.
 */
export async function startTranscription(
  audio: Audio,
  opts: TranscriptionOptions = {},
  callbacks: TranscriptionCallbacks = {},
): Promise<void> {
  if (isTranscribing(audio.id)) return;

  // fraction=null: fase de carga do modelo (antes do 1º segmento).
  patch(audio.id, { fraction: null });
  try {
    const result = await transcribe(
      {
        audio_path: audio.path,
        audio_id: audio.id,
        model: opts.model ?? null,
        device: opts.device,
      },
      (fraction) => patch(audio.id, { fraction }),
    );
    callbacks.onDone?.(result);
  } catch (e) {
    callbacks.onError?.(e instanceof Error ? e.message : String(e));
  } finally {
    patch(audio.id, null);
  }
}
