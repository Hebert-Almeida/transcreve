<script lang="ts">
  import { t } from "$lib/i18n";
  import { errorMessage, interpolate } from "$lib/format";

  /** Uma opção de exportação: rótulo + a ação que baixa e salva (devolve o caminho ou null). */
  export interface ExportOption {
    label: string;
    run: () => Promise<string | null>;
  }

  let { options }: { options: ExportOption[] } = $props();

  let open = $state(false);
  let busy = $state(false);
  // Resultado transitório da última exportação (sucesso ou erro).
  let toast = $state<{ kind: "ok" | "error"; text: string } | null>(null);

  async function choose(option: ExportOption) {
    open = false;
    busy = true;
    toast = null;
    try {
      const path = await option.run();
      if (path) {
        toast = { kind: "ok", text: interpolate($t.export.saved, { path }) };
      }
    } catch (e) {
      toast = {
        kind: "error",
        text: interpolate($t.export.failed, { error: errorMessage(e) }),
      };
    } finally {
      busy = false;
      if (toast) setTimeout(() => (toast = null), 4000);
    }
  }
</script>

<div class="relative inline-block">
  <button
    class="rounded-[var(--radius-app)] border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-[var(--color-surface-muted)] disabled:opacity-50"
    disabled={busy}
    onclick={() => (open = !open)}
  >
    {$t.export.button}
  </button>

  {#if open}
    <!-- Camada para fechar ao clicar fora -->
    <button
      class="fixed inset-0 z-10 cursor-default"
      aria-label={$t.common.cancel}
      onclick={() => (open = false)}
    ></button>
    <div
      class="absolute right-0 z-20 mt-1 min-w-44 overflow-hidden rounded-[var(--radius-app)] border border-[var(--color-border)] bg-[var(--color-surface)] py-1 shadow-lg"
    >
      {#each options as option (option.label)}
        <button
          class="block w-full px-4 py-1.5 text-left text-sm hover:bg-[var(--color-surface-muted)]"
          onclick={() => choose(option)}
        >
          {option.label}
        </button>
      {/each}
    </div>
  {/if}
</div>

{#if toast}
  <p
    class="mt-2 rounded-[var(--radius-app)] px-3 py-1.5 text-xs
      {toast.kind === 'ok'
      ? 'bg-green-500/10 text-green-700 dark:text-green-400'
      : 'bg-red-500/10 text-red-600 dark:text-red-400'}"
  >
    {toast.text}
  </p>
{/if}
