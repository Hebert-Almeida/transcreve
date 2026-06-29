/**
 * Projeto atualmente selecionado, compartilhado entre as telas (Projetos →
 * Transcrição → Análise). Persistido no localStorage para sobreviver à navegação
 * e a recarregamentos.
 */
import { writable } from "svelte/store";
import { browser } from "$app/environment";

const KEY = "transcreve:selectedProject";

function initial(): number | null {
  if (!browser) return null;
  const raw = localStorage.getItem(KEY);
  const n = raw ? Number(raw) : NaN;
  return Number.isFinite(n) ? n : null;
}

export const selectedProjectId = writable<number | null>(initial());

if (browser) {
  selectedProjectId.subscribe((id) => {
    if (id == null) localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, String(id));
  });
}
