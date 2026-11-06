import { describe, expect, it } from 'vitest';

import { openPalette } from '@/lib/command-palette';

const commands = [
  { name: 'summarise', help: 'Recap the conversation' },
  { name: 'handoff', help: 'Hand this to a colleague' },
  { name: 'sources', help: 'Show what was used' },
];

describe('openPalette', () => {
  it('stays closed for ordinary text', () => {
    expect(openPalette('what happened?', commands).open).toBe(false);
  });

  it('opens on a lone slash and offers everything', () => {
    const shown = openPalette('/', commands);
    expect(shown.open).toBe(true);
    expect(shown.matches).toHaveLength(3);
  });

  it('narrows as you type', () => {
    expect(openPalette('/s', commands).matches.map((c) => c.name)).toEqual([
      'summarise',
      'sources',
    ]);
  });

  it('matches on the help text too, because people search by what it does', () => {
    expect(openPalette('/colleague', commands).matches.map((c) => c.name)).toEqual(['handoff']);
  });

  it('ignores case', () => {
    expect(openPalette('/HAND', commands).matches.map((c) => c.name)).toEqual(['handoff']);
  });

  it('puts a name match above a help match', () => {
    const shown = openPalette('/s', [
      { name: 'zebra', help: 'summarise things' },
      { name: 'summarise', help: 'Recap' },
    ]);
    expect(shown.matches[0].name).toBe('summarise');
  });

  it('says plainly when nothing matches', () => {
    const shown = openPalette('/nonsense', commands);
    expect(shown.matches).toEqual([]);
    expect(shown.emptyMessage).toContain('No command');
  });

  it('closes once a command is complete and an argument is being typed', () => {
    expect(openPalette('/summarise in two lines', commands).open).toBe(false);
  });

  it('stays open while the name is still ambiguous', () => {
    expect(openPalette('/su', commands).open).toBe(true);
  });

  it('does not open for a slash inside a sentence', () => {
    expect(openPalette('and/or', commands).open).toBe(false);
  });
});
