<script lang="ts">
  import { formatTime } from "$lib/format";
  import type { Segment, CodingMap, AssignedCode } from "$lib/sidecar/client";

  let {
    segments,
    coding = {},
    activeSegmentId = null,
    onSegmentClick,
  }: {
    segments: Segment[];
    /** Mapa segment_id -> códigos, para marcar trechos codificados. */
    coding?: CodingMap;
    /** Trecho atualmente em foco (codificação aberta). */
    activeSegmentId?: number | null;
    /** Quando definido, cada trecho fica clicável (modo codificação). */
    onSegmentClick?: (segment: Segment) => void;
  } = $props();

  // Agrupa segmentos consecutivos do mesmo falante (quando houver diarização).
  type Block = { speaker: string | null; segments: Segment[] };

  let blocks = $derived.by<Block[]>(() => {
    const out: Block[] = [];
    for (const seg of segments) {
      const last = out[out.length - 1];
      if (last && last.speaker === seg.speaker) last.segments.push(seg);
      else out.push({ speaker: seg.speaker, segments: [seg] });
    }
    return out;
  });

  function codesFor(seg: Segment): AssignedCode[] {
    return coding[String(seg.id)] ?? [];
  }

  // Cor do primeiro código do trecho — usada para o sublinhado da marcação.
  function markColor(seg: Segment): string | null {
    const c = codesFor(seg);
    return c.length ? (c[0].color ?? "var(--color-accent)") : null;
  }
</script>

<div class="space-y-4 leading-relaxed">
  {#each blocks as block}
    <p>
      {#if block.speaker}
        <span class="mr-1 font-semibold text-[var(--color-accent)]">{block.speaker}:</span>
      {/if}
      <!-- Cada trecho mostra o timestamp no hover; no modo codificação, é clicável.
           span clicável (não <button>) para fluir no texto corrido; tem role e teclado. -->
      {#each block.segments as seg, i (seg.id)}
        {#if i > 0}<span> </span>{/if}
        <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
        <span
          role={onSegmentClick ? "button" : undefined}
          tabindex={onSegmentClick ? 0 : undefined}
          class="rounded px-0.5 transition
            {onSegmentClick ? 'cursor-pointer hover:bg-[var(--color-surface-muted)]' : 'cursor-default'}
            {activeSegmentId === seg.id ? 'bg-[var(--color-accent)]/15 ring-1 ring-[var(--color-accent)]' : ''}"
          style={markColor(seg)
            ? `text-decoration: underline; text-decoration-color: ${markColor(seg)}; text-decoration-thickness: 2px; text-underline-offset: 3px;`
            : undefined}
          title={`${formatTime(seg.start)} – ${formatTime(seg.end)}`}
          onclick={() => onSegmentClick?.(seg)}
          onkeydown={(e) => {
            if (onSegmentClick && (e.key === "Enter" || e.key === " ")) {
              e.preventDefault();
              onSegmentClick(seg);
            }
          }}
        >{seg.text}</span>
      {/each}
    </p>
  {/each}
</div>
