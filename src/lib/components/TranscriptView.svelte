<script lang="ts">
  import { t } from "$lib/i18n";
  import { formatTime } from "$lib/format";
  import type { Segment } from "$lib/sidecar/client";

  let { segments }: { segments: Segment[] } = $props();

  // Agrupa segmentos consecutivos do mesmo falante (quando houver diarização).
  // Por ora speaker costuma ser null e tudo cai num bloco único de texto corrido.
  type Block = { speaker: string | null; segments: Segment[] };

  let blocks = $derived.by<Block[]>(() => {
    const out: Block[] = [];
    for (const seg of segments) {
      const last = out[out.length - 1];
      if (last && last.speaker === seg.speaker) {
        last.segments.push(seg);
      } else {
        out.push({ speaker: seg.speaker, segments: [seg] });
      }
    }
    return out;
  });
</script>

<div class="space-y-4 leading-relaxed">
  {#each blocks as block}
    <p>
      {#if block.speaker}
        <span class="mr-1 font-semibold text-[var(--color-accent)]">
          {block.speaker}:
        </span>
      {/if}
      <!-- Cada trecho mostra o timestamp no hover (title nativo + estilo sutil). -->
      {#each block.segments as seg, i (seg.id)}
        {#if i > 0}{" "}{/if}<span
          class="cursor-default rounded px-0.5 transition hover:bg-[var(--color-surface-muted)]"
          title={`${formatTime(seg.start)} – ${formatTime(seg.end)}`}
        >{seg.text}</span>
      {/each}
    </p>
  {/each}
</div>
