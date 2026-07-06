<script lang="ts">
  import { onMount } from "svelte";
  import { t } from "$lib/i18n";
  import PageHeader from "$lib/components/PageHeader.svelte";
  import TranscriptView from "$lib/components/TranscriptView.svelte";
  import ExportMenu, { type ExportOption } from "$lib/components/ExportMenu.svelte";
  import { formatDuration } from "$lib/format";
  import {
    projects as projectApi,
    audios as audioApi,
    exports as exportApi,
    TRANSCRIPT_FORMATS,
    type Project,
    type Audio,
    type Segment,
  } from "$lib/sidecar/client";
  import { selectedProjectId } from "$lib/stores/selection";
  import { model, device } from "$lib/stores/settings";
  import { activeTranscriptions, startTranscription } from "$lib/stores/transcription";

  let projects = $state<Project[]>([]);
  let audios = $state<Audio[]>([]);
  let selectedAudio = $state<Audio | null>(null);
  let segments = $state<Segment[]>([]);
  let error = $state<string | null>(null);

  // Estado "em transcrição" vem do store global (sobrevive à troca de aba):
  // um áudio está travado enquanto estiver no mapa; a fração alimenta a barra.
  function isBusy(id: number): boolean {
    return $activeTranscriptions.has(id);
  }
  function progressOf(id: number): number | null | undefined {
    return $activeTranscriptions.get(id)?.fraction;
  }

  // Carrega projetos para o seletor; reage à mudança de projeto selecionado.
  onMount(async () => {
    try {
      projects = await projectApi.list();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  });

  // Recarrega áudios quando o projeto selecionado muda.
  $effect(() => {
    const pid = $selectedProjectId;
    selectedAudio = null;
    segments = [];
    if (pid == null) {
      audios = [];
      return;
    }
    audioApi
      .list(pid)
      .then((list) => (audios = list))
      .catch((e) => (error = e instanceof Error ? e.message : String(e)));
  });

  async function importAudio() {
    const pid = $selectedProjectId;
    if (pid == null) return;
    error = null;
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        multiple: false,
        filters: [
          {
            name: "Áudio",
            extensions: ["mp3", "wav", "m4a", "ogg", "flac", "aac", "wma", "opus"],
          },
        ],
      });
      if (typeof selected !== "string") return; // cancelado
      const filename = selected.split(/[\\/]/).pop() ?? selected;
      const audio = await audioApi.create(pid, { path: selected, filename });
      audios = [audio, ...audios];
      selectAudio(audio);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  async function selectAudio(audio: Audio) {
    selectedAudio = audio;
    segments = [];
    if (audio.status === "done") {
      try {
        segments = await audioApi.segments(audio.id);
      } catch (e) {
        error = e instanceof Error ? e.message : String(e);
      }
    }
  }

  function runTranscription(audio: Audio) {
    error = null;
    // Otimista: marca como processando na lista.
    patchAudio(audio.id, { status: "processing" });
    // Delega ao store global — a transcrição continua mesmo se sairmos da aba.
    // Os callbacks reconciliam o estado local (lista + painel) ao concluir; se
    // o usuário estiver noutra aba, o servidor persiste do mesmo jeito e o
    // $effect recarrega do banco ao voltar.
    void startTranscription(
      audio,
      { model: $model, device: $device },
      {
        onDone: (result) => {
          patchAudio(audio.id, {
            status: "done",
            duration: result.duration,
            language: result.language,
            model: result.model,
            device: result.device,
          });
          if (selectedAudio?.id === audio.id) {
            selectedAudio = { ...selectedAudio, status: "done" };
            segments = result.segments.map((s) => ({ ...s, audio_id: audio.id }));
          }
        },
        onError: (message) => {
          patchAudio(audio.id, { status: "error" });
          if (selectedAudio?.id === audio.id) error = message;
        },
      },
    );
  }

  function patchAudio(id: number, patch: Partial<Audio>) {
    audios = audios.map((a) => (a.id === id ? { ...a, ...patch } : a));
  }

  function statusLabel(status: string): string {
    const s = $t.transcription.status as Record<string, string>;
    return s[status] ?? status;
  }

  let fullText = $derived(segments.map((s) => s.text).join(" "));
  let copied = $state(false);

  // Opções de exportação da transcrição do áudio selecionado. Tabela (RStudio),
  // legenda e documento — derivadas de TRANSCRIPT_FORMATS (fonte única). A
  // codificação só vai nos formatos que a suportam (tabela/documento, não legenda).
  function audioExportOptions(audioId: number): ExportOption[] {
    return TRANSCRIPT_FORMATS.map(({ fmt, kind, supportsCoding }) => ({
      label: `${fmt.toUpperCase()} · ${$t.export[kind]}`,
      run: () =>
        exportApi.audioTranscript(audioId, fmt, { coding: supportsCoding }),
    }));
  }

  async function copyText() {
    await navigator.clipboard.writeText(fullText);
    copied = true;
    setTimeout(() => (copied = false), 1500);
  }
</script>

<PageHeader title={$t.transcription.title} />

<section class="px-8 py-6">
  <!-- Seletor de projeto -->
  <div class="mb-6 flex flex-wrap items-center gap-3">
    <select
      class="rounded-[var(--radius-app)] border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--color-accent)]"
      value={$selectedProjectId ?? ""}
      onchange={(e) => {
        const v = (e.target as HTMLSelectElement).value;
        selectedProjectId.set(v ? Number(v) : null);
      }}
    >
      <option value="">{$t.transcription.selectProject}</option>
      {#each projects as p (p.id)}
        <option value={p.id}>{p.name}</option>
      {/each}
    </select>

    {#if $selectedProjectId != null}
      <button
        class="rounded-[var(--radius-app)] border border-[var(--color-border)] px-4 py-2 text-sm font-medium hover:bg-[var(--color-surface-muted)]"
        onclick={importAudio}
      >
        {$t.transcription.importAudio}
      </button>
    {/if}
  </div>

  {#if error}
    <p class="mb-4 rounded-[var(--radius-app)] bg-red-500/10 px-4 py-2 text-sm text-red-600 dark:text-red-400">
      {error}
    </p>
  {/if}

  {#if $selectedProjectId == null}
    <div class="rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]">
      {$t.transcription.noProject}
    </div>
  {:else}
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
      <!-- Lista de áudios -->
      <aside>
        <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-content-muted)]">
          {$t.transcription.audios}
        </h2>
        {#if audios.length === 0}
          <p class="text-sm text-[var(--color-content-muted)]">{$t.transcription.noAudios}</p>
        {:else}
          <ul class="space-y-1">
            {#each audios as audio (audio.id)}
              <li>
                <button
                  class="w-full rounded-[var(--radius-app)] border px-3 py-2 text-left text-sm transition
                    {selectedAudio?.id === audio.id
                    ? 'border-[var(--color-accent)] bg-[var(--color-surface-muted)]'
                    : 'border-transparent hover:bg-[var(--color-surface-muted)]'}"
                  onclick={() => selectAudio(audio)}
                >
                  <span class="block truncate font-medium">{audio.filename}</span>
                  <span class="flex items-center gap-1.5 text-xs text-[var(--color-content-muted)]">
                    {#if isBusy(audio.id)}
                      <span class="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-[var(--color-accent)] border-t-transparent"></span>
                    {/if}
                    {statusLabel(audio.status)}
                    {#if audio.duration}· {formatDuration(audio.duration)}{/if}
                  </span>
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </aside>

      <!-- Painel de transcrição -->
      <main>
        {#if !selectedAudio}
          <div class="rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]">
            {$t.transcription.status.idle}
          </div>
        {:else}
          <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 class="font-medium">{selectedAudio.filename}</h2>
              <p class="text-xs text-[var(--color-content-muted)]">
                {statusLabel(selectedAudio.status)}
                {#if selectedAudio.language}· {selectedAudio.language.toUpperCase()}{/if}
                {#if selectedAudio.model}· {selectedAudio.model}{/if}
              </p>
            </div>
            <div class="flex gap-2">
              {#if segments.length > 0}
                <button
                  class="rounded-[var(--radius-app)] border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-[var(--color-surface-muted)]"
                  onclick={copyText}
                >
                  {copied ? $t.transcription.copied : $t.transcription.copyText}
                </button>
                <ExportMenu options={audioExportOptions(selectedAudio.id)} />
              {/if}
              <button
                class="rounded-[var(--radius-app)] bg-[var(--color-accent)] px-3 py-1.5 text-sm font-medium text-[var(--color-accent-content)] hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isBusy(selectedAudio.id)}
                onclick={() => runTranscription(selectedAudio!)}
              >
                {selectedAudio.status === "done"
                  ? $t.transcription.retranscribe
                  : $t.transcription.transcribe}
              </button>
            </div>
          </div>

          {#if isBusy(selectedAudio.id)}
            {@const fraction = progressOf(selectedAudio.id)}
            <div class="rounded-[var(--radius-app)] border border-[var(--color-border)] px-4 py-6">
              <div class="mb-3 flex items-center justify-between text-sm text-[var(--color-content-muted)]">
                <span class="flex items-center gap-2">
                  {#if fraction == null}
                    <span class="h-4 w-4 animate-spin rounded-full border-2 border-[var(--color-accent)] border-t-transparent"></span>
                    {$t.transcription.preparingModel}
                  {:else}
                    {$t.transcription.transcribing}
                  {/if}
                </span>
                {#if fraction != null}
                  <span class="tabular-nums font-medium text-[var(--color-content)]">
                    {Math.round(fraction * 100)}%
                  </span>
                {/if}
              </div>
              <!-- Trilha da barra: determinada (largura = fração) ou indeterminada
                   (listra animada) enquanto o modelo carrega. -->
              <div class="h-2 w-full overflow-hidden rounded-full bg-[var(--color-surface-muted)]">
                {#if fraction == null}
                  <div class="progress-indeterminate h-full w-1/3 rounded-full bg-[var(--color-accent)]"></div>
                {:else}
                  <div
                    class="h-full rounded-full bg-[var(--color-accent)] transition-[width] duration-300 ease-out"
                    style="width: {Math.round(fraction * 100)}%"
                  ></div>
                {/if}
              </div>
            </div>
          {:else if segments.length > 0}
            <article class="rounded-[var(--radius-app)] border border-[var(--color-border)] p-6 text-[15px]">
              <TranscriptView {segments} />
            </article>
          {:else if selectedAudio.status === "error"}
            <p class="text-sm text-red-600 dark:text-red-400">{$t.transcription.status.error}</p>
          {:else}
            <div class="rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]">
              {$t.transcription.status.idle}
            </div>
          {/if}
        {/if}
      </main>
    </div>
  {/if}
</section>

<style>
  /* Barra indeterminada: uma listra desliza da esquerda p/ a direita enquanto o
     modelo carrega (fração ainda desconhecida). */
  @keyframes progress-indeterminate {
    0% {
      transform: translateX(-100%);
    }
    100% {
      transform: translateX(400%);
    }
  }
  .progress-indeterminate {
    animation: progress-indeterminate 1.2s ease-in-out infinite;
  }
</style>
