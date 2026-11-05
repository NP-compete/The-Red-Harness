export interface PaletteCommand {
  name: string;
  help: string;
}

export interface Palette {
  open: boolean;
  matches: PaletteCommand[];
  emptyMessage?: string;
}

const CLOSED: Palette = { open: false, matches: [] };

export function openPalette(input: string, commands: PaletteCommand[]): Palette {
  if (!input.startsWith('/')) return CLOSED;

  const typed = input.slice(1);
  // Once there is a space the name is settled and the rest is an
  // argument, so the list would only be in the way.
  if (typed.includes(' ')) return CLOSED;

  const needle = typed.toLowerCase();
  const byName = commands.filter((c) => c.name.toLowerCase().includes(needle));
  // Help text only matches once there is enough to go on: a single
  // letter appears in almost every description.
  const byHelp =
    needle.length >= 3
      ? commands.filter((c) => !byName.includes(c) && c.help.toLowerCase().includes(needle))
      : [];
  const matches = [...byName, ...byHelp];

  return {
    open: true,
    matches,
    emptyMessage: matches.length === 0 ? `No command matches "${typed}"` : undefined,
  };
}
