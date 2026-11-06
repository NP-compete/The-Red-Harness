import type { ReadItem } from '../components/ReadMaterial';
import type { KeptPassage } from './duplicate-sources-view';

export interface DedupedReads {
  kept: KeptPassage[];
  /** The results behind `kept`, in step, so their descriptions survive. */
  originals: ReadItem[];
  /** How many repeats were folded away. */
  collapsed: number;
}

// The agent's fencing is plumbing; two passages differing only by it
// are the same passage.
const MARKER = /<<<external-content[^>]*>>>/g;

/** The same passage from two places is one passage, twice confirmed. */
export function dedupeReads(reads: ReadItem[]): DedupedReads {
  const byText = new Map<string, { first: ReadItem; sources: string[] }>();
  let collapsed = 0;

  for (const read of reads) {
    const key = read.text.replace(MARKER, '').replace(/\s+/g, ' ').trim();
    const seen = byText.get(key);
    if (!seen) {
      byText.set(key, { first: read, sources: [read.source] });
      continue;
    }
    collapsed += 1;
    // One source repeating itself is still one source.
    if (!seen.sources.includes(read.source)) {
      seen.sources.push(read.source);
    }
  }

  const folded = [...byText.values()];
  const kept = folded.map<KeptPassage>(({ first, sources }) => {
    const alsoIn = sources.slice(1);
    return {
      source: first.source,
      text: first.text,
      // Not reported by the agent, and unused by the view.
      score: 0,
      // Nothing ranks these, and claiming one is informal would invent
      // a judgement nobody made.
      authority: 'unknown',
      alsoIn,
      corroborated: alsoIn.length > 0,
    };
  });

  return { kept, originals: folded.map(({ first }) => first), collapsed };
}
