import type ptBR from "./locales/pt-BR";

/**
 * Substitui valores literais de string por `string`, preservando a estrutura
 * de chaves. Assim PT-BR define a *forma* das traduções (fonte da verdade),
 * mas EN/ES podem ter qualquer texto.
 */
type DeepStringify<T> = {
  [K in keyof T]: T[K] extends string ? string : DeepStringify<T[K]>;
};

/** PT-BR é a fonte da verdade: todas as traduções devem ter as mesmas chaves. */
export type Translation = DeepStringify<typeof ptBR>;

export const LOCALES = ["pt-BR", "en", "es"] as const;
export type Locale = (typeof LOCALES)[number];

export const LOCALE_LABELS: Record<Locale, string> = {
  "pt-BR": "Português (Brasil)",
  en: "English",
  es: "Español",
};
