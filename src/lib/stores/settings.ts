/**
 * Configurações do motor de transcrição (modelo e dispositivo), persistidas no
 * localStorage para sobreviver à navegação e a recarregamentos. Espelha o padrão
 * de `stores/selection.ts` e `stores/theme.ts`.
 *
 * Apenas os modelos embarcados no bundle offline são oferecidos: `large-v3-turbo`
 * (padrão) e `small`.
 */
import { writable } from "svelte/store";
import { browser } from "$app/environment";

export const MODELS = ["large-v3-turbo", "small"] as const;
export type Model = (typeof MODELS)[number];

export const DEVICES = ["auto", "cpu", "cuda"] as const;
export type Device = (typeof DEVICES)[number];

const MODEL_KEY = "transcreve:model";
const DEVICE_KEY = "transcreve:device";

const DEFAULT_MODEL: Model = "large-v3-turbo";
const DEFAULT_DEVICE: Device = "auto";

function initialModel(): Model {
  if (!browser) return DEFAULT_MODEL;
  const saved = localStorage.getItem(MODEL_KEY);
  return (MODELS as readonly string[]).includes(saved ?? "")
    ? (saved as Model)
    : DEFAULT_MODEL;
}

function initialDevice(): Device {
  if (!browser) return DEFAULT_DEVICE;
  const saved = localStorage.getItem(DEVICE_KEY);
  return (DEVICES as readonly string[]).includes(saved ?? "")
    ? (saved as Device)
    : DEFAULT_DEVICE;
}

export const model = writable<Model>(initialModel());
export const device = writable<Device>(initialDevice());

if (browser) {
  model.subscribe((m) => localStorage.setItem(MODEL_KEY, m));
  device.subscribe((d) => localStorage.setItem(DEVICE_KEY, d));
}
