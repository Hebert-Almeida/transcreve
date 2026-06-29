<script lang="ts">
  import { onMount } from "svelte";
  import { t } from "$lib/i18n";
  import PageHeader from "$lib/components/PageHeader.svelte";
  import QualitativeCoding from "$lib/components/QualitativeCoding.svelte";
  import { projects as projectApi, type Project } from "$lib/sidecar/client";
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
  {:else}
    <div class="rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]">
      {$t.common.loading}
    </div>
  {/if}
</section>
