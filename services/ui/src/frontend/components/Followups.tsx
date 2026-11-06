import { presentFollowups } from '../lib/followups-view';

interface FollowupsProps {
  /** Parts of the question the answer never reached. */
  uncovered: string[];
  onAsk: (question: string) => void;
}

/** What the reader could ask next, taken from what this answer missed. */
export function Followups({ uncovered, onAsk }: FollowupsProps) {
  const followups = presentFollowups({
    // Suggested only where the turn can show its working: each of these
    // is a part of the question the answer demonstrably did not reach.
    offered: uncovered.map((text) => ({ text, because: 'your question' })),
    setAside: 0,
    reason: '',
  });

  if (!followups) {
    return null;
  }

  return (
    <div className="mt-1 flex flex-wrap items-center gap-1.5">
      <span className="text-[11px] text-muted-foreground">{followups.prompt}</span>
      {followups.chips.map((chip) => (
        <button
          key={chip.sends}
          type="button"
          className="rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
          onClick={() => onAsk(chip.sends)}
        >
          {chip.text}
        </button>
      ))}
    </div>
  );
}
