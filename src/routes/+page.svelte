<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { t } from "$lib/i18n";
  import PageHeader from "$lib/components/PageHeader.svelte";
  import { projects as api, type Project } from "$lib/sidecar/client";
  import { selectedProjectId } from "$lib/stores/selection";

  let projects = $state<Project[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  // Formulário de criação inline.
  let creating = $state(false);
  let newName = $state("");
  let newDescription = $state("");
  let saving = $state(false);

  async function load() {
    loading = true;
    error = null;
    try {
      projects = await api.list();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }

  async function create() {
    const name = newName.trim();
    if (!name) return;
    saving = true;
    try {
      const project = await api.create(name, newDescription.trim() || undefined);
      projects = [project, ...projects];
      newName = "";
      newDescription = "";
      creating = false;
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      saving = false;
    }
  }

  async function remove(project: Project) {
    if (!confirm($t.projects.deleteConfirm)) return;
    try {
      await api.remove(project.id);
      projects = projects.filter((p) => p.id !== project.id);
      if ($selectedProjectId === project.id) selectedProjectId.set(null);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  function open(project: Project) {
    selectedProjectId.set(project.id);
    goto("/transcription");
  }

  onMount(load);
</script>

<PageHeader title={$t.projects.title} subtitle={$t.app.tagline} />

<section class="px-8 py-6">
  <div class="mb-6 flex items-center justify-between">
    {#if !creating}
      <button
        class="rounded-[var(--radius-app)] bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-[var(--color-accent-content)] hover:opacity-90"
        onclick={() => (creating = true)}
      >
        + {$t.projects.create}
      </button>
    {/if}
  </div>

  {#if creating}
    <form
      class="mb-6 space-y-3 rounded-[var(--radius-app)] border border-[var(--color-border)] p-4"
      onsubmit={(e) => {
        e.preventDefault();
        create();
      }}
    >
      <!-- svelte-ignore a11y_autofocus — foco no campo ao abrir o formulário de criação é intencional -->
      <input
        class="w-full rounded-[var(--radius-app)] border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--color-accent)]"
        placeholder={$t.projects.namePlaceholder}
        bind:value={newName}
        autofocus
      />
      <input
        class="w-full rounded-[var(--radius-app)] border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--color-accent)]"
        placeholder={$t.projects.description}
        bind:value={newDescription}
      />
      <div class="flex gap-2">
        <button
          type="submit"
          disabled={!newName.trim() || saving}
          class="rounded-[var(--radius-app)] bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-[var(--color-accent-content)] hover:opacity-90 disabled:opacity-50"
        >
          {$t.common.save}
        </button>
        <button
          type="button"
          class="rounded-[var(--radius-app)] border border-[var(--color-border)] px-4 py-2 text-sm hover:bg-[var(--color-surface-muted)]"
          onclick={() => {
            creating = false;
            newName = "";
            newDescription = "";
          }}
        >
          {$t.common.cancel}
        </button>
      </div>
    </form>
  {/if}

  {#if error}
    <p class="mb-4 rounded-[var(--radius-app)] bg-red-500/10 px-4 py-2 text-sm text-red-600 dark:text-red-400">
      {error}
    </p>
  {/if}

  {#if loading}
    <p class="text-sm text-[var(--color-content-muted)]">{$t.common.loading}</p>
  {:else if projects.length === 0}
    <div
      class="rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]"
    >
      {$t.projects.empty}
    </div>
  {:else}
    <ul class="grid grid-cols-2 gap-4 lg:grid-cols-3">
      {#each projects as project (project.id)}
        <li
          class="group flex flex-col rounded-[var(--radius-app)] border border-[var(--color-border)] p-4 transition hover:border-[var(--color-accent)]"
        >
          <button class="flex-1 text-left" onclick={() => open(project)}>
            <h3 class="font-medium">{project.name}</h3>
            {#if project.description}
              <p class="mt-1 line-clamp-2 text-sm text-[var(--color-content-muted)]">
                {project.description}
              </p>
            {/if}
          </button>
          <div class="mt-4 flex items-center justify-between">
            <button
              class="text-sm font-medium text-[var(--color-accent)] hover:underline"
              onclick={() => open(project)}
            >
              {$t.projects.open} →
            </button>
            <button
              class="text-sm text-[var(--color-content-muted)] opacity-0 transition group-hover:opacity-100 hover:text-red-500"
              onclick={() => remove(project)}
              aria-label={$t.common.delete}
            >
              {$t.common.delete}
            </button>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</section>
