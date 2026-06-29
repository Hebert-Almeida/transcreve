<script lang="ts">
  import { t } from "$lib/i18n";
  import { formatTime, errorMessage as msg } from "$lib/format";
  import TranscriptView from "$lib/components/TranscriptView.svelte";
  import {
    audios as audioApi,
    codes as codeApi,
    analysis as analysisApi,
    type Audio,
    type Segment,
    type Code,
    type CodingMap,
    type QualitativeSummary,
  } from "$lib/sidecar/client";

  let { projectId }: { projectId: number } = $props();

  let audios = $state<Audio[]>([]);
  let selectedAudio = $state<Audio | null>(null);
  let segments = $state<Segment[]>([]);
  let coding = $state<CodingMap>({});
  let codes = $state<Code[]>([]);
  let summary = $state<QualitativeSummary | null>(null);
  let activeSegment = $state<Segment | null>(null);
  let error = $state<string | null>(null);

  let newCodeName = $state("");
  let newCodeColor = $state("#2563eb");

  // Paleta sugerida para novos códigos.
  const palette = [
    "#e11d48", "#2563eb", "#16a34a", "#d97706",
    "#7c3aed", "#0891b2", "#db2777", "#65a30d",
  ];

  // Carrega áudios + códigos + resumo quando o projeto muda.
  $effect(() => {
    const pid = projectId;
    reset();
    Promise.all([audioApi.list(pid), codeApi.list(pid)])
      .then(([a, c]) => {
        audios = a.filter((x) => x.status === "done");
        codes = c;
      })
      .catch((e) => (error = msg(e)));
    refreshSummary();
  });

  function reset() {
    selectedAudio = null;
    segments = [];
    coding = {};
    activeSegment = null;
  }

  async function refreshSummary() {
    try {
      summary = await analysisApi.qualitative(projectId);
    } catch (e) {
      error = msg(e);
    }
  }

  async function selectAudio(audio: Audio) {
    selectedAudio = audio;
    activeSegment = null;
    error = null;
    try {
      const [segs, cod] = await Promise.all([
        audioApi.segments(audio.id),
        audioApi.coding(audio.id),
      ]);
      segments = segs;
      coding = cod;
    } catch (e) {
      error = msg(e);
    }
  }

  async function createCode() {
    const name = newCodeName.trim();
    if (!name) return;
    try {
      const code = await codeApi.create(projectId, name, newCodeColor);
      codes = [...codes, code].sort((a, b) => a.name.localeCompare(b.name));
      newCodeName = "";
      // Avança a cor sugerida para a próxima da paleta.
      const idx = palette.indexOf(newCodeColor);
      newCodeColor = palette[(idx + 1) % palette.length];
    } catch (e) {
      error = msg(e);
    }
  }

  function isAssigned(segment: Segment, codeId: number): boolean {
    return (coding[String(segment.id)] ?? []).some((c) => c.id === codeId);
  }

  async function toggleCode(code: Code) {
    if (!activeSegment) return;
    const seg = activeSegment;
    const key = String(seg.id);
    const assigned = isAssigned(seg, code.id);
    try {
      if (assigned) {
        await codeApi.unassign(seg.id, code.id);
        coding[key] = (coding[key] ?? []).filter((c) => c.id !== code.id);
        if (coding[key].length === 0) delete coding[key];
      } else {
        await codeApi.assign(seg.id, code.id);
        coding[key] = [
          ...(coding[key] ?? []),
          { id: code.id, name: code.name, color: code.color, memo: null },
        ];
      }
      coding = { ...coding }; // dispara reatividade
      refreshSummary();
    } catch (e) {
      error = msg(e);
    }
  }

  let coveragePct = $derived(summary ? Math.round(summary.coverage * 100) : 0);
</script>

{#if error}
  <p class="mb-4 rounded-[var(--radius-app)] bg-red-500/10 px-4 py-2 text-sm text-red-600 dark:text-red-400">
    {error}
  </p>
{/if}

<div class="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
  <!-- Coluna principal: seletor de áudio + transcrição codificável -->
  <div>
    <select
      class="mb-4 rounded-[var(--radius-app)] border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--color-accent)]"
      value={selectedAudio?.id ?? ""}
      onchange={(e) => {
        const v = (e.target as HTMLSelectElement).value;
        const a = audios.find((x) => x.id === Number(v));
        if (a) selectAudio(a);
      }}
    >
      <option value="">{$t.analysis.selectAudio}</option>
      {#each audios as a (a.id)}
        <option value={a.id}>{a.filename}</option>
      {/each}
    </select>

    {#if !selectedAudio}
      <div class="rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]">
        {$t.analysis.clickToCode}
      </div>
    {:else if segments.length === 0}
      <div class="rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]">
        {$t.analysis.needTranscription}
      </div>
    {:else}
      <article class="rounded-[var(--radius-app)] border border-[var(--color-border)] p-6 text-[15px]">
        <TranscriptView
          {segments}
          {coding}
          activeSegmentId={activeSegment?.id ?? null}
          onSegmentClick={(s) => (activeSegment = s)}
        />
      </article>
    {/if}
  </div>

  <!-- Coluna lateral: códigos + painel do trecho + métricas -->
  <aside class="space-y-6">
    <!-- Gerenciar códigos -->
    <div>
      <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-content-muted)]">
        {$t.analysis.codes}
      </h3>
      <form
        class="mb-3 flex gap-2"
        onsubmit={(e) => {
          e.preventDefault();
          createCode();
        }}
      >
        <input
          type="color"
          class="h-9 w-9 shrink-0 cursor-pointer rounded border border-[var(--color-border)] bg-transparent"
          bind:value={newCodeColor}
          aria-label="Cor"
        />
        <input
          class="min-w-0 flex-1 rounded-[var(--radius-app)] border border-[var(--color-border)] bg-transparent px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent)]"
          placeholder={$t.analysis.codeName}
          bind:value={newCodeName}
        />
        <button
          type="submit"
          disabled={!newCodeName.trim()}
          class="rounded-[var(--radius-app)] bg-[var(--color-accent)] px-3 py-1.5 text-sm font-medium text-[var(--color-accent-content)] hover:opacity-90 disabled:opacity-50"
        >
          +
        </button>
      </form>
    </div>

    <!-- Painel do trecho selecionado -->
    {#if activeSegment}
      <div class="rounded-[var(--radius-app)] border border-[var(--color-border)] p-3">
        <p class="mb-1 text-xs text-[var(--color-content-muted)]">
          {$t.analysis.selectedSegment} · {formatTime(activeSegment.start)}–{formatTime(activeSegment.end)}
        </p>
        <p class="mb-3 text-sm italic">"{activeSegment.text}"</p>
        {#if codes.length === 0}
          <p class="text-xs text-[var(--color-content-muted)]">{$t.analysis.noCodes}</p>
        {:else}
          <div class="flex flex-wrap gap-1.5">
            {#each codes as code (code.id)}
              {@const on = isAssigned(activeSegment, code.id)}
              <button
                class="rounded-full border px-2.5 py-1 text-xs font-medium transition
                  {on ? 'text-white' : 'text-[var(--color-content)] hover:bg-[var(--color-surface-muted)]'}"
                style={on
                  ? `background-color: ${code.color ?? "#2563eb"}; border-color: ${code.color ?? "#2563eb"};`
                  : `border-color: ${code.color ?? "var(--color-border)"};`}
                onclick={() => toggleCode(code)}
              >
                {code.name}
              </button>
            {/each}
          </div>
        {/if}
      </div>
    {/if}

    <!-- Métricas: cobertura + frequências + co-ocorrência -->
    {#if summary}
      <div>
        <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-content-muted)]">
          {$t.analysis.coverage}
        </h3>
        <div class="rounded-[var(--radius-app)] border border-[var(--color-border)] p-3">
          <div class="flex items-baseline justify-between">
            <span class="text-2xl font-semibold">{coveragePct}%</span>
            <span class="text-xs text-[var(--color-content-muted)]">
              {summary.coded_segments}/{summary.total_segments} {$t.analysis.segments}
            </span>
          </div>
          <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--color-surface-muted)]">
            <div class="h-full bg-[var(--color-accent)]" style={`width: ${coveragePct}%`}></div>
          </div>
        </div>
      </div>

      <div>
        <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-content-muted)]">
          {$t.analysis.frequencies}
        </h3>
        {#if summary.codes.every((c) => c.segment_count === 0)}
          <p class="text-xs text-[var(--color-content-muted)]">{$t.analysis.noCoding}</p>
        {:else}
          <ul class="space-y-1.5">
            {#each summary.codes.filter((c) => c.segment_count > 0) as c (c.id)}
              <li class="flex items-center gap-2 text-sm">
                <span class="h-3 w-3 shrink-0 rounded-full" style={`background-color: ${c.color ?? "#2563eb"}`}></span>
                <span class="flex-1 truncate">{c.name}</span>
                <span class="text-xs text-[var(--color-content-muted)]">
                  {c.segment_count} · {c.word_count} {$t.analysis.words}
                </span>
              </li>
            {/each}
          </ul>
        {/if}
      </div>

      {#if summary.cooccurrence.length > 0}
        <div>
          <h3 class="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--color-content-muted)]">
            {$t.analysis.cooccurrence}
          </h3>
          <p class="mb-2 text-xs text-[var(--color-content-muted)]">{$t.analysis.cooccurrenceHint}</p>
          <ul class="space-y-1 text-sm">
            {#each summary.cooccurrence as pair (`${pair.code_a}-${pair.code_b}`)}
              <li class="flex items-center justify-between">
                <span class="truncate">{pair.name_a} ↔ {pair.name_b}</span>
                <span class="text-xs text-[var(--color-content-muted)]">{pair.count}</span>
              </li>
            {/each}
          </ul>
        </div>
      {/if}
    {/if}
  </aside>
</div>
