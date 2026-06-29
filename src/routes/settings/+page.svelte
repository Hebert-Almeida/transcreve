<script lang="ts">
  import { t, locale, setLocale, LOCALES, LOCALE_LABELS, type Locale } from "$lib/i18n";
  import { theme, setTheme, type ThemeMode } from "$lib/stores/theme";
  import { model, device, MODELS } from "$lib/stores/settings";
  import PageHeader from "$lib/components/PageHeader.svelte";

  // Motor: modelo e dispositivo são persistidos no store settings (localStorage).
  let diarization = $state(true);

  const themeModes: ThemeMode[] = ["light", "dark", "system"];
  const themeLabel = $derived({
    light: $t.common.themeLight,
    dark: $t.common.themeDark,
    system: $t.common.themeSystem,
  });
</script>

<PageHeader title={$t.settings.title} />

<section class="max-w-2xl px-8 py-6">
  <!-- Aparência -->
  <div class="mb-8">
    <h3 class="mb-3 text-sm font-semibold">{$t.common.theme}</h3>
    <div class="flex gap-2">
      {#each themeModes as mode (mode)}
        <button
          onclick={() => setTheme(mode)}
          class="rounded-[var(--radius-app)] border px-4 py-2 text-sm transition-colors
            {$theme === mode
            ? 'border-[var(--color-accent)] bg-[var(--color-accent)] text-[var(--color-accent-content)]'
            : 'border-[var(--color-border)] hover:bg-[var(--color-surface-muted)]'}"
        >
          {themeLabel[mode]}
        </button>
      {/each}
    </div>
  </div>

  <!-- Idioma -->
  <div class="mb-8">
    <h3 class="mb-3 text-sm font-semibold">{$t.common.language}</h3>
    <select
      value={$locale}
      onchange={(e) => setLocale((e.currentTarget as HTMLSelectElement).value as Locale)}
      class="rounded-[var(--radius-app)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
    >
      {#each LOCALES as l (l)}
        <option value={l}>{LOCALE_LABELS[l]}</option>
      {/each}
    </select>
  </div>

  <!-- Motor de transcrição -->
  <div class="mb-8">
    <h3 class="mb-3 text-sm font-semibold">{$t.settings.engine}</h3>

    <label class="mb-4 block">
      <span class="mb-1 block text-xs text-[var(--color-content-muted)]">{$t.settings.model}</span>
      <select
        bind:value={$model}
        class="w-full rounded-[var(--radius-app)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
      >
        {#each MODELS as m (m)}
          <option value={m}>{m}</option>
        {/each}
      </select>
    </label>

    <label class="mb-4 block">
      <span class="mb-1 block text-xs text-[var(--color-content-muted)]">{$t.settings.device}</span>
      <select
        bind:value={$device}
        class="w-full rounded-[var(--radius-app)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
      >
        <option value="auto">{$t.settings.deviceAuto}</option>
        <option value="cpu">{$t.settings.deviceCpu}</option>
        <option value="cuda">{$t.settings.deviceGpu}</option>
      </select>
    </label>

    <label class="flex items-center gap-2 text-sm">
      <input type="checkbox" bind:checked={diarization} class="accent-[var(--color-accent)]" />
      {$t.settings.diarization}
    </label>
  </div>
</section>
