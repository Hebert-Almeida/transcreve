<script lang="ts">
  import "../app.css";
  import { page } from "$app/state";
  import { t, locale, setLocale, LOCALES, LOCALE_LABELS, type Locale } from "$lib/i18n";
  import { theme, setTheme, type ThemeMode } from "$lib/stores/theme";

  let { children } = $props();

  const nav = $derived([
    { href: "/", key: "projects", label: $t.nav.projects },
    { href: "/transcription", key: "transcription", label: $t.nav.transcription },
    { href: "/analysis", key: "analysis", label: $t.nav.analysis },
    { href: "/settings", key: "settings", label: $t.nav.settings },
  ]);

  function isActive(href: string): boolean {
    if (href === "/") return page.url.pathname === "/";
    return page.url.pathname.startsWith(href);
  }

  const themeIcons: Record<ThemeMode, string> = {
    light: "☀️",
    dark: "🌙",
    system: "🖥️",
  };

  function cycleTheme() {
    const order: ThemeMode[] = ["light", "dark", "system"];
    const next = order[(order.indexOf($theme) + 1) % order.length];
    setTheme(next);
  }
</script>

<div class="flex h-screen overflow-hidden">
  <!-- Barra lateral minimalista -->
  <aside
    class="flex w-56 shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-surface-muted)]"
  >
    <div class="px-5 py-5">
      <h1 class="text-lg font-semibold tracking-tight">{$t.app.name}</h1>
      <p class="mt-1 text-xs leading-snug text-[var(--color-content-muted)]">
        {$t.app.tagline}
      </p>
    </div>

    <nav class="flex-1 px-3">
      {#each nav as item (item.key)}
        <a
          href={item.href}
          class="mb-1 block rounded-[var(--radius-app)] px-3 py-2 text-sm font-medium transition-colors
            {isActive(item.href)
            ? 'bg-[var(--color-accent)] text-[var(--color-accent-content)]'
            : 'text-[var(--color-content-muted)] hover:bg-[var(--color-border)] hover:text-[var(--color-content)]'}"
        >
          {item.label}
        </a>
      {/each}
    </nav>

    <!-- Rodapé: tema + idioma -->
    <div class="flex items-center justify-between gap-2 border-t border-[var(--color-border)] px-3 py-3">
      <button
        onclick={cycleTheme}
        title={$t.common.theme}
        class="rounded-[var(--radius-app)] px-2 py-1 text-sm hover:bg-[var(--color-border)]"
        aria-label={$t.common.theme}
      >
        {themeIcons[$theme]}
      </button>

      <select
        value={$locale}
        onchange={(e) => setLocale((e.currentTarget as HTMLSelectElement).value as Locale)}
        class="flex-1 rounded-[var(--radius-app)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-xs"
        aria-label={$t.common.language}
      >
        {#each LOCALES as l (l)}
          <option value={l}>{LOCALE_LABELS[l]}</option>
        {/each}
      </select>
    </div>
  </aside>

  <!-- Conteúdo -->
  <main class="flex-1 overflow-y-auto">
    {@render children()}
  </main>
</div>
