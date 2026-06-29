<script lang="ts">
  import { t } from "$lib/i18n";
  import PageHeader from "$lib/components/PageHeader.svelte";

  let tab: "quantitative" | "qualitative" | "sentiment" = $state("quantitative");
</script>

<PageHeader title={$t.analysis.title} />

<section class="px-8 py-6">
  <div class="mb-6 flex gap-1 border-b border-[var(--color-border)]">
    {#each [["quantitative", $t.analysis.quantitative], ["qualitative", $t.analysis.qualitative], ["sentiment", $t.analysis.sentiment]] as [key, label] (key)}
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

  <div class="rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]">
    {$t.common.loading}
  </div>
</section>
