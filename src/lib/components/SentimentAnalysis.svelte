<script lang="ts">
  import { t } from "$lib/i18n";
  import { formatTime, errorMessage as msg } from "$lib/format";
  import {
    analysis as analysisApi,
    type SentimentSummary,
    type SentimentDistribution,
    type SentimentLabel,
  } from "$lib/sidecar/client";

  let { projectId }: { projectId: number } = $props();

  let summary = $state<SentimentSummary | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);

  // Recarrega quando o projeto muda.
  $effect(() => {
    const pid = projectId;
    loading = true;
    error = null;
    analysisApi
      .sentiment(pid)
      .then((s) => (summary = s))
      .catch((e) => (error = msg(e)))
      .finally(() => (loading = false));
  });

  // Cor por rótulo, reutilizada nas barras, pontos e chips.
  const COLORS: Record<SentimentLabel, string> = {
    positive: "var(--color-positive, #16a34a)",
    negative: "var(--color-negative, #dc2626)",
    neutral: "var(--color-content-muted)",
  };
  const label = (key: SentimentLabel) => $t.analysis[key];

  // Ordem de exibição das fatias da distribuição.
  const ORDER: SentimentLabel[] = ["positive", "negative", "neutral"];

  function total(d: SentimentDistribution): number {
    return d.positive + d.negative + d.neutral;
  }

  // Percentual de cada rótulo numa distribuição (para a barra empilhada).
  function pct(d: SentimentDistribution, key: SentimentLabel): number {
    const tot = total(d);
    return tot ? (d[key] / tot) * 100 : 0;
  }
</script>

{#if error}
  <p class="mb-4 rounded-[var(--radius-app)] bg-red-500/10 px-4 py-2 text-sm text-red-600 dark:text-red-400">
    {error}
  </p>
{:else if loading}
  <div class="rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]">
    {$t.common.loading}
  </div>
{:else if !summary || summary.total_segments === 0}
  <div class="rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]">
    {$t.analysis.noTranscriptions}
  </div>
{:else}
  <!-- Visão geral: distribuição do projeto + polaridade média -->
  <h3 class="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-content-muted)]">
    {$t.analysis.overview}
  </h3>
  <div class="mb-2 flex h-3 overflow-hidden rounded-full">
    {#each ORDER as key (key)}
      {@const p = pct(summary.distribution, key)}
      {#if p > 0}
        <span style={`width: ${p}%; background: ${COLORS[key]}`} title={label(key)}></span>
      {/if}
    {/each}
  </div>
  <div class="mb-8 flex flex-wrap gap-x-5 gap-y-1 text-sm">
    {#each ORDER as key (key)}
      <span class="flex items-center gap-1.5">
        <span class="h-2.5 w-2.5 rounded-full" style={`background: ${COLORS[key]}`}></span>
        {label(key)}
        <span class="tabular-nums text-[var(--color-content-muted)]">{summary.distribution[key]}</span>
      </span>
    {/each}
    <span class="flex items-center gap-1.5 text-[var(--color-content-muted)]">
      {$t.analysis.avgPolarity}:
      <span class="tabular-nums text-[var(--color-content)]">{summary.avg_polarity.toFixed(2)}</span>
    </span>
  </div>

  <div class="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_360px]">
    <!-- Linha do tempo -->
    <div>
      <h3 class="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--color-content-muted)]">
        {$t.analysis.sentimentTimeline}
      </h3>
      <p class="mb-3 text-xs text-[var(--color-content-muted)]">{$t.analysis.sentimentTimelineHint}</p>
      <ul class="space-y-1.5">
        {#each summary.timeline as point (point.segment_id)}
          <li class="flex items-start gap-3 text-sm">
            <span class="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full" style={`background: ${COLORS[point.label]}`} title={label(point.label)}></span>
            <span class="w-16 shrink-0 pt-px text-xs tabular-nums text-[var(--color-content-muted)]">
              {formatTime(point.start)}
            </span>
            <span class="min-w-0 flex-1 truncate">{point.text}</span>
            <span class="shrink-0 pt-px text-xs tabular-nums text-[var(--color-content-muted)]">
              {point.polarity > 0 ? "+" : ""}{point.polarity.toFixed(2)}
            </span>
          </li>
        {/each}
      </ul>
    </div>

    <!-- Recorte por áudio -->
    <aside>
      <h3 class="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-content-muted)]">
        {$t.analysis.perAudio}
      </h3>
      <ul class="space-y-2">
        {#each summary.audios as a (a.audio_id)}
          <li class="rounded-[var(--radius-app)] border border-[var(--color-border)] p-3">
            <div class="mb-1.5 flex items-baseline justify-between gap-2">
              <p class="min-w-0 truncate text-sm font-medium">{a.filename}</p>
              <span class="shrink-0 text-xs tabular-nums text-[var(--color-content-muted)]">
                {a.avg_polarity > 0 ? "+" : ""}{a.avg_polarity.toFixed(2)}
              </span>
            </div>
            <div class="flex h-2 overflow-hidden rounded-full">
              {#each ORDER as key (key)}
                {@const p = pct(a.distribution, key)}
                {#if p > 0}
                  <span style={`width: ${p}%; background: ${COLORS[key]}`} title={label(key)}></span>
                {/if}
              {/each}
            </div>
          </li>
        {/each}
      </ul>
    </aside>
  </div>
{/if}
