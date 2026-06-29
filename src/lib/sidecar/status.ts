import { writable } from "svelte/store";
import { browser } from "$app/environment";
import { health } from "./client";

export type SidecarStatus = "connecting" | "online" | "offline";

/** Estado de conexão com o sidecar, para indicador visual na UI. */
export const sidecarStatus = writable<SidecarStatus>("connecting");

let started = false;

/** Inicia o monitoramento periódico do sidecar (idempotente). */
export function startMonitoring(intervalMs = 5000) {
  if (!browser || started) return;
  started = true;

  const ping = async () => {
    try {
      await health();
      sidecarStatus.set("online");
    } catch {
      sidecarStatus.set("offline");
    }
  };

  void ping();
  setInterval(ping, intervalMs);
}
