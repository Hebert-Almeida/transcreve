import type { Translation } from "../types";

// English
const en: Translation = {
  app: {
    name: "Transcreve",
    tagline: "Transcription and analysis of research audio — local and confidential",
  },
  nav: {
    projects: "Projects",
    transcription: "Transcription",
    analysis: "Analysis",
    settings: "Settings",
  },
  common: {
    new: "New",
    open: "Open",
    save: "Save",
    cancel: "Cancel",
    delete: "Delete",
    export: "Export",
    search: "Search",
    loading: "Loading…",
    language: "Language",
    theme: "Theme",
    themeLight: "Light",
    themeDark: "Dark",
    themeSystem: "System",
  },
  projects: {
    title: "Projects",
    empty: "No projects yet.",
    create: "New project",
    name: "Project name",
  },
  transcription: {
    title: "Transcription",
    importAudio: "Import audio",
    speaker: "Speaker",
    start: "Start",
    end: "End",
    text: "Text",
    status: {
      idle: "Idle",
      queued: "Queued",
      running: "Transcribing…",
      done: "Done",
      error: "Error",
    },
  },
  analysis: {
    title: "Analysis",
    quantitative: "Quantitative",
    qualitative: "Qualitative",
    sentiment: "Sentiment",
    wordCount: "Total words",
    speakingTime: "Speaking time",
    speakingRate: "Rate (words/min)",
    lexicalRichness: "Lexical richness",
  },
  settings: {
    title: "Settings",
    engine: "Transcription engine",
    model: "Model",
    device: "Processing",
    deviceAuto: "Automatic",
    deviceCpu: "CPU",
    deviceGpu: "GPU (CUDA)",
    diarization: "Diarization (identify speakers)",
  },
};

export default en;
