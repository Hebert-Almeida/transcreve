import { writable } from "svelte/store";
import { browser } from "$app/environment";

export type ThemeMode = "light" | "dark" | "system";

const STORAGE_KEY = "transcreve:theme";

function detectInitial(): ThemeMode {
  if (!browser) return "system";
  const saved = localStorage.getItem(STORAGE_KEY) as ThemeMode | null;
  // O app.html grava "dark"/"light"; tratamos ausência como "system".
  if (saved === "light" || saved === "dark") return saved;
  return "system";
}

/** Modo de tema escolhido pelo usuário. */
export const theme = writable<ThemeMode>(detectInitial());

function systemPrefersDark(): boolean {
  return browser && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function apply(mode: ThemeMode) {
  if (!browser) return;
  const dark = mode === "dark" || (mode === "system" && systemPrefersDark());
  document.documentElement.classList.toggle("dark", dark);
  if (mode === "system") {
    localStorage.removeItem(STORAGE_KEY);
  } else {
    localStorage.setItem(STORAGE_KEY, mode);
  }
}

theme.subscribe(apply);

if (browser) {
  // Reage a mudanças do tema do sistema quando o modo é "system".
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    let current: ThemeMode = "system";
    theme.subscribe((v) => (current = v))();
    if (current === "system") apply("system");
  });
}

export function setTheme(mode: ThemeMode) {
  theme.set(mode);
}
