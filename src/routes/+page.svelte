<script lang="ts">
  import { t } from "$lib/i18n";
  import PageHeader from "$lib/components/PageHeader.svelte";

  // Placeholder até a persistência SQLite entrar (fase de projetos).
  const projects: { id: string; name: string }[] = $state([]);
</script>

<PageHeader title={$t.projects.title} subtitle={$t.app.tagline} />

<section class="px-8 py-6">
  <div class="mb-6 flex items-center justify-between">
    <button
      class="rounded-[var(--radius-app)] bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-[var(--color-accent-content)] hover:opacity-90"
    >
      + {$t.projects.create}
    </button>
  </div>

  {#if projects.length === 0}
    <div
      class="rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]"
    >
      {$t.projects.empty}
    </div>
  {:else}
    <ul class="grid grid-cols-2 gap-4 lg:grid-cols-3">
      {#each projects as project (project.id)}
        <li class="rounded-[var(--radius-app)] border border-[var(--color-border)] p-4">
          {project.name}
        </li>
      {/each}
    </ul>
  {/if}
</section>
