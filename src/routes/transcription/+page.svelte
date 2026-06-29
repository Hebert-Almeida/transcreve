<script lang="ts">
  import { t } from "$lib/i18n";
  import PageHeader from "$lib/components/PageHeader.svelte";
</script>

<PageHeader title={$t.transcription.title} />

<section class="px-8 py-6">
  <button
    class="rounded-[var(--radius-app)] border border-[var(--color-border)] px-4 py-2 text-sm font-medium hover:bg-[var(--color-surface-muted)]"
  >
    {$t.transcription.importAudio}
  </button>

  <div class="mt-6 rounded-[var(--radius-app)] border border-dashed border-[var(--color-border)] px-8 py-16 text-center text-sm text-[var(--color-content-muted)]">
    {$t.transcription.status.idle}
  </div>
</section>
