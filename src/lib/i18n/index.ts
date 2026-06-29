import { derived, writable } from "svelte/store";
import { browser } from "$app/environment";
import ptBR from "./locales/pt-BR";
import en from "./locales/en";
import es from "./locales/es";
import { LOCALES, type Locale, type Translation } from "./types";

export { LOCALES, LOCALE_LABELS, type Locale } from "./types";

const dictionaries: Record<Locale, Translation> = {
  "pt-BR": ptBR,
  en,
  es,
};

const STORAGE_KEY = "transcreve:locale";

function detectInitialLocale(): Locale {
  if (!browser) return "pt-BR";
  const saved = localStorage.getItem(STORAGE_KEY) as Locale | null;
  if (saved && LOCALES.includes(saved)) return saved;
  const nav = navigator.language.toLowerCase();
  if (nav.startsWith("pt")) return "pt-BR";
  if (nav.startsWith("es")) return "es";
  if (nav.startsWith("en")) return "en";
  return "pt-BR";
}

/** Idioma atual da interface. */
export const locale = writable<Locale>(detectInitialLocale());

locale.subscribe((value) => {
  if (browser) {
    localStorage.setItem(STORAGE_KEY, value);
    document.documentElement.lang = value;
  }
});

export function setLocale(value: Locale) {
  locale.set(value);
}

/** Dicionário de traduções reativo ao idioma selecionado. */
export const t = derived(locale, ($locale) => dictionaries[$locale]);
