import { useEffect, useState } from 'react';

import { openPalette, type PaletteCommand } from '../lib/command-palette';

interface CommandPaletteProps {
  input: string;
  commands: PaletteCommand[];
  onPick: (name: string) => void;
}

/** The commands available, while a slash is being typed. */
export function CommandPalette({ input, commands, onPick }: CommandPaletteProps) {
  const palette = openPalette(input, commands);
  // What the box said when it was dismissed. Typing moves on from
  // it, which is what brings the list back.
  const [dismissedAt, setDismissedAt] = useState<string | null>(null);

  // Listened for on the window, not the list: the slash is typed in
  // the composer, so that is where the focus is when somebody wants
  // the suggestions gone.
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDismissedAt(input);
    };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [input]);

  // An empty palette is a surface with nothing on it.
  if (!palette.open || commands.length === 0 || dismissedAt === input) {
    return null;
  }

  return (
    <ul
      role="listbox"
      aria-label="Commands"
      className="mx-3 mb-2 max-h-56 overflow-auto rounded-lg border border-border bg-card p-1 list-none"
    >
      {palette.matches.map((command) => (
        <li
          key={command.name}
          role="option"
          aria-selected={false}
          tabIndex={0}
          onClick={() => onPick(command.name)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') onPick(command.name);
          }}
          className="flex cursor-pointer items-baseline gap-2 rounded px-2 py-1.5 hover:bg-secondary/60"
        >
          <span className="font-mono text-xs text-foreground">/{command.name}</span>
          <span className="text-xs text-muted-foreground">{command.help}</span>
        </li>
      ))}
      {palette.emptyMessage && (
        <li className="px-2 py-1.5 text-xs text-muted-foreground">{palette.emptyMessage}</li>
      )}
    </ul>
  );
}
