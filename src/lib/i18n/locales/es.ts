import type { Translation } from "../types";

// Español
const es: Translation = {
  app: {
    name: "Transcreve",
    tagline: "Transcripción y análisis de audios de investigación — local y confidencial",
  },
  nav: {
    projects: "Proyectos",
    transcription: "Transcripción",
    analysis: "Análisis",
    settings: "Configuración",
  },
  common: {
    new: "Nuevo",
    open: "Abrir",
    save: "Guardar",
    cancel: "Cancelar",
    delete: "Eliminar",
    export: "Exportar",
    search: "Buscar",
    loading: "Cargando…",
    language: "Idioma",
    theme: "Tema",
    themeLight: "Claro",
    themeDark: "Oscuro",
    themeSystem: "Sistema",
  },
  projects: {
    title: "Proyectos",
    empty: "Aún no hay proyectos.",
    create: "Nuevo proyecto",
    name: "Nombre del proyecto",
  },
  transcription: {
    title: "Transcripción",
    importAudio: "Importar audio",
    speaker: "Hablante",
    start: "Inicio",
    end: "Fin",
    text: "Texto",
    status: {
      idle: "En espera",
      queued: "En cola",
      running: "Transcribiendo…",
      done: "Completado",
      error: "Error",
    },
  },
  analysis: {
    title: "Análisis",
    quantitative: "Cuantitativo",
    qualitative: "Cualitativo",
    sentiment: "Sentimiento",
    wordCount: "Total de palabras",
    speakingTime: "Tiempo de habla",
    speakingRate: "Velocidad (palabras/min)",
    lexicalRichness: "Riqueza léxica",
  },
  settings: {
    title: "Configuración",
    engine: "Motor de transcripción",
    model: "Modelo",
    device: "Procesamiento",
    deviceAuto: "Automático",
    deviceCpu: "CPU",
    deviceGpu: "GPU (CUDA)",
    diarization: "Diarización (identificar hablantes)",
  },
};

export default es;
