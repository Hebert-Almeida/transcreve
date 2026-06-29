<script lang="ts">
  let { title, subtitle }: { title: string; subtitle?: string } = $props();
</script>

<header class="border-b border-[var(--color-border)] px-8 py-5">
  <h2 class="text-xl font-semibold tracking-tight">{title}</h2>
  {#if subtitle}
    <p class="mt-1 text-sm text-[var(--color-content-muted)]">{subtitle}</p>
  {/if}
</header>
