import { useEffect, useState } from 'react';

import {
  openReferences,
  replaceReference,
  type Known,
} from '../lib/reference-palette';

interface ReferencePaletteProps {
  input: string;
  known: Known;
  /** The whole sentence, with the reference finished. */
  onPick: (input: string) => void;
}

/** Specialists and documents, while one is being named. */
export function ReferencePalette({ input, known, onPick }: ReferencePaletteProps) {
  const palette = openReferences(input, known);
  // What the box said when it was dismissed. Typing moves on from
  // it, which is what brings the list back.
  const [dismissedAt, setDismissedAt] = useState<string | null>(null);

  // On the window rather than the list: the character is typed in
  // the composer, so that is where the focus is when somebody wants
  // the suggestions gone.
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDismissedAt(input);
    };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [input]);

  if (!palette.open || dismissedAt === input) {
    return null;
  }

  const marker = palette.kind === 'document' ? '#' : '@';

  return (
    <ul
      role="listbox"
      aria-label="References"
      className="mx-3 mb-2 max-h-56 overflow-auto rounded-lg border border-border bg-card p-1 list-none"
    >
      {palette.matches.map((one) => (
        <li
          key={`${one.kind}-${one.name}`}
          role="option"
          aria-selected={false}
          tabIndex={0}
          onClick={() => onPick(replaceReference(input, one.name))}
          onKeyDown={(event) => {
            if (event.key === 'Enter') onPick(replaceReference(input, one.name));
          }}
          className="flex cursor-pointer items-baseline gap-2 rounded px-2 py-1.5 hover:bg-secondary/60"
        >
          <span className="font-mono text-xs text-foreground">
            {one.kind === 'document' ? '#' : '@'}
            {one.name}
          </span>
          <span className="text-xs text-muted-foreground">{one.about}</span>
        </li>
      ))}
      {palette.emptyMessage && (
        <li className="px-2 py-1.5 text-xs text-muted-foreground">
          {palette.emptyMessage}
          <span className="sr-only"> for {marker}</span>
        </li>
      )}
    </ul>
  );
}
