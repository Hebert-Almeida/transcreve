<script lang="ts">
  import { onMount } from "svelte";
  import { t } from "$lib/i18n";
  import PageHeader from "$lib/components/PageHeader.svelte";
  import QualitativeCoding from "$lib/components/QualitativeCoding.svelte";
  import QuantitativeAnalysis from "$lib/components/QuantitativeAnalysis.svelte";
  import SentimentAnalysis from "$lib/components/SentimentAnalysis.svelte";
  import ExportMenu, { type ExportOption } from "$lib/components/ExportMenu.svelte";
  import {
    projects as projectApi,
    exports as exportApi,
    type Project,
    type TranscriptFormat,
    type AnalysisExportFormat,
  } from "$lib/sidecar/client";
  import { selectedProjectId } from "$lib/stores/selection";

  let tab: "quantitative" | "qualitative" | "sentiment" = $state("qualitative");
  let projects = $state<Project[]>([]);

  onMount(async () => {
    try {
      projects = await projectApi.list();
    } catch {
      /* erro tratado nas telas filhas */
    }
  });

  // Exportações do projeto: a transcrição inteira (com codificação) e, nas abas
  // quantitativa/sentimento, também o resultado da análise atual em tabela/JSON.
  function projectExportOptions(pid: number): ExportOption[] {
    const transcriptFmts: TranscriptFormat[] = [
      "csv",
      "tsv",
      "json",
      "srt",
      "vtt",
      "docx",
      "pdf",
    ];
    const opts: ExportOption[] = transcriptFmts.map((fmt) => ({
      label: `${$t.export.transcriptProject} · ${fmt.toUpperCase()}`,
      run: () =>
        exportApi.projectTranscript(pid, fmt, {
          coding: fmt !== "srt" && fmt !== "vtt",
        }),
    }));

    // Resultado da análise só faz sentido nas abas com payload exportável.
    if (tab === "quantitative" || tab === "sentiment") {
      const kind = tab; // fixa o tipo estreitado para o closure
      const analysisFmts: AnalysisExportFormat[] = ["csv", "tsv", "json"];
      for (const fmt of analysisFmts) {
        opts.push({
          label: `${$t.export.analysis} · ${fmt.toUpperCase()}`,
          run: () => exportApi.analysis(pid, kind, fmt),
        });
      }
    }
    return opts;
  }
</script>

<PageHeader title={$t.analysis.title} />

<section class="px-8 py-6">
  <!-- Seletor de projeto + abas -->
  <div class="mb-6 flex flex-wrap items-center gap-3">
    <select
      class="rounded-[var(--radius-app)] border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--color-accent)]"
      value={$selectedProjectId ?? ""}
      onchange={(e) => {
        const v = (e.target as HTMLSelectElement).value;
        selectedProjectId.set(v ? Number(v) : null);
      }}
    >
      <option value="">{$t.analysis.selectProject}</option>
      {#each projects as p (p.id)}
        <option value={p.id}>{p.name}</option>
      {/each}
    </select>

    {#if $selectedProjectId != null}
      <ExportMenu options={projectExportOptions($selectedProjectId)} />
    {/if}
  </div>

  <div class="mb-6 flex gap-1 border-b border-[var(--color-border)]">
    {#each [["qualitative", $t.analysis.qualitative], ["quantitative", $t.analysis.quantitative], ["sentiment", $t.analysis.sentiment]] as [key, label] (key)}
      <button
        onclick={() => (tab = key as typeof tab)}
        class="-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors
          {tab === key
          ? 'border-[var(--color-accent)] text-[var(--color-content)]'
          : 'border-transparent text-[var(--color-content-muted)] hover:text-[var(--color-content)]'}"
      >
        {label}
      </button>
    {/each}
  </div>

  {#if $selectedProjectId == null}
    <div class="rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]">
      {$t.analysis.selectProject}
    </div>
  {:else if tab === "qualitative"}
    {#key $selectedProjectId}
      <QualitativeCoding projectId={$selectedProjectId} />
    {/key}
  {:else if tab === "quantitative"}
    {#key $selectedProjectId}
      <QuantitativeAnalysis projectId={$selectedProjectId} />
    {/key}
  {:else}
    {#key $selectedProjectId}
      <SentimentAnalysis projectId={$selectedProjectId} />
    {/key}
  {/if}
</section>
