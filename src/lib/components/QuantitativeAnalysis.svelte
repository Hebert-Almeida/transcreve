<script lang="ts">
  import { t } from "$lib/i18n";
  import { formatDuration } from "$lib/format";
  import {
    analysis as analysisApi,
    type QuantitativeSummary,
  } from "$lib/sidecar/client";

  let { projectId }: { projectId: number } = $props();

  let summary = $state<QuantitativeSummary | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);

  function msg(e: unknown): string {
    return e instanceof Error ? e.message : String(e);
  }

  // Recarrega quando o projeto muda.
  $effect(() => {
    const pid = projectId;
    loading = true;
    error = null;
    analysisApi
      .quantitative(pid)
      .then((s) => (summary = s))
      .catch((e) => (error = msg(e)))
      .finally(() => (loading = false));
  });

  // Maior contagem entre os termos, para dimensionar as barras.
  let maxTerm = $derived(
    summary && summary.top_terms.length > 0
      ? summary.top_terms[0].count
      : 1,
  );

  let hasData = $derived(summary != null && summary.audios.length > 0);
</script>

{#if error}
  <p class="mb-4 rounded-[var(--radius-app)] bg-red-500/10 px-4 py-2 text-sm text-red-600 dark:text-red-400">
    {error}
  </p>
{:else if loading}
  <div class="rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]">
    {$t.common.loading}
  </div>
{:else if !hasData}
  <div class="rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]">
    {$t.analysis.noTranscriptions}
  </div>
{:else if summary}
  <!-- Cartões de visão geral -->
  <h3 class="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-content-muted)]">
    {$t.analysis.overview}
  </h3>
  <div class="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
    {#each [[$t.analysis.wordCount, summary.word_count.toLocaleString()], [$t.analysis.uniqueWords, summary.unique_words.toLocaleString()], [$t.analysis.speakingTime, formatDuration(summary.spoken_seconds)], [$t.analysis.speakingRate, String(summary.speaking_rate)], [$t.analysis.lexicalRichness, summary.lexical_richness.toFixed(2)]] as [label, value] (label)}
      <div class="rounded-[var(--radius-app)] border border-[var(--color-border)] p-3">
        <p class="text-2xl font-semibold tabular-nums">{value}</p>
        <p class="mt-1 text-xs text-[var(--color-content-muted)]">{label}</p>
      </div>
    {/each}
  </div>

  <div class="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_360px]">
    <!-- Termos mais frequentes -->
    <div>
      <h3 class="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--color-content-muted)]">
        {$t.analysis.topTerms}
      </h3>
      <p class="mb-3 text-xs text-[var(--color-content-muted)]">{$t.analysis.topTermsHint}</p>
      {#if summary.top_terms.length === 0}
        <p class="text-xs text-[var(--color-content-muted)]">{$t.analysis.noTranscriptions}</p>
      {:else}
        <ul class="space-y-1.5">
          {#each summary.top_terms as term (term.term)}
            <li class="flex items-center gap-3 text-sm">
              <span class="w-32 shrink-0 truncate">{term.term}</span>
              <span class="h-2 rounded-full bg-[var(--color-accent)]" style={`width: ${Math.max(4, (term.count / maxTerm) * 100)}%`}></span>
              <span class="shrink-0 text-xs tabular-nums text-[var(--color-content-muted)]">{term.count}</span>
            </li>
          {/each}
        </ul>
      {/if}
    </div>

    <!-- Recorte por áudio -->
    <aside>
      <h3 class="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-content-muted)]">
        {$t.analysis.perAudio}
      </h3>
      <ul class="space-y-2">
        {#each summary.audios as a (a.audio_id)}
          <li class="rounded-[var(--radius-app)] border border-[var(--color-border)] p-3">
            <p class="mb-1.5 truncate text-sm font-medium">{a.filename}</p>
            <div class="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-[var(--color-content-muted)]">
              <span>{a.word_count.toLocaleString()} {$t.analysis.words}</span>
              <span>{formatDuration(a.spoken_seconds)}</span>
              <span>{a.speaking_rate} p/min</span>
              <span>{$t.analysis.lexicalRichness}: {a.lexical_richness.toFixed(2)}</span>
            </div>
          </li>
        {/each}
      </ul>
    </aside>
  </div>
{/if}
