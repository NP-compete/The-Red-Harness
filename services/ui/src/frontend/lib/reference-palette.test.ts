import { describe, expect, it } from 'vitest';

import { openReferences, replaceReference } from './reference-palette';

const KNOWN = {
  subagents: [
    { name: 'curator', about: 'Finds data and says whether it can be trusted' },
    { name: 'critic', about: 'Checks an answer against its sources' },
  ],
  documents: [
    { name: 'notes.md', about: '1.2 kB' },
    { name: 'offsite-plan.md', about: '4.0 kB' },
  ],
};

describe('openReferences', () => {
  it('stays shut until something is referenced', () => {
    expect(openReferences('what is the fee', KNOWN).open).toBe(false);
  });

  it('offers the specialists when a person reaches for one', () => {
    const found = openReferences('ask @', KNOWN);
    expect(found.matches.map((m) => m.name)).toEqual(['curator', 'critic']);
  });

  it('offers the documents when a person reaches for one', () => {
    const found = openReferences('look at #', KNOWN);
    expect(found.matches.map((m) => m.name)).toEqual(['notes.md', 'offsite-plan.md']);
  });

  it('narrows as they type', () => {
    expect(openReferences('ask @cur', KNOWN).matches.map((m) => m.name)).toEqual([
      'curator',
    ]);
  });

  it('does not care about case', () => {
    expect(openReferences('ask @CUR', KNOWN).matches.map((m) => m.name)).toEqual([
      'curator',
    ]);
  });

  it('works part way through a sentence', () => {
    expect(openReferences('please ask @cri', KNOWN).matches.map((m) => m.name)).toEqual([
      'critic',
    ]);
  });

  it('says so when nothing matches', () => {
    const found = openReferences('ask @zzz', KNOWN);
    expect(found.open).toBe(true);
    expect(found.emptyMessage).toMatch(/zzz/);
  });

  it('closes again once the reference is finished', () => {
    expect(openReferences('ask @curator about the fee', KNOWN).open).toBe(false);
  });

  it('does not open on an email address', () => {
    expect(openReferences('write to sam@example', KNOWN).open).toBe(false);
  });

  it('does not open on a hash inside a word', () => {
    expect(openReferences('issue ABC#123', KNOWN).open).toBe(false);
  });

  it('opens on something that merely looks like a reference, and says nothing matches', () => {
    // A colour and a filename are the same shape, so the list cannot
    // tell them apart — it can only decline to offer anything.
    const found = openReferences('the colour #ff0000', KNOWN);
    expect(found.matches).toEqual([]);
    expect(found.emptyMessage).toMatch(/ff0000/);
  });

  it('says which kind each match is', () => {
    expect(openReferences('ask @', KNOWN).matches[0].kind).toBe('subagent');
    expect(openReferences('see #', KNOWN).matches[0].kind).toBe('document');
  });

  it('offers nothing a person cannot already see', () => {
    const found = openReferences('ask @', { subagents: [], documents: [] });
    expect(found.matches).toEqual([]);
  });

  it('says which kind it opened for even when nothing matches', () => {
    const found = openReferences('see #zzz', { subagents: [], documents: [] });
    expect(found.kind).toBe('document');
  });

  it('knows a specialist was asked for even when there are none', () => {
    expect(openReferences('ask @', { subagents: [], documents: [] }).kind).toBe(
      'subagent',
    );
  });
});

describe('replaceReference', () => {
  it('finishes the reference being typed', () => {
    expect(replaceReference('ask @cur', 'curator')).toBe('ask @curator ');
  });

  it('keeps the rest of the sentence', () => {
    expect(replaceReference('please ask @cri', 'critic')).toBe('please ask @critic ');
  });

  it('keeps the character that started it', () => {
    expect(replaceReference('look at #not', 'notes.md')).toBe('look at #notes.md ');
  });

  it('leaves a sentence with no reference alone', () => {
    expect(replaceReference('what is the fee', 'curator')).toBe('what is the fee');
  });
});

describe('a specialist described at length', () => {
  const wordy = {
    subagents: [
      {
        name: 'curator',
        about:
          'Finds data and establishes whether it can be trusted. Use for "where is the data for X", who owns this, and impact analysis before a schema change.',
      },
    ],
    documents: [],
  };

  it('is offered with one line, not its whole description', () => {
    const [match] = openReferences('ask @', wordy).matches;
    expect(match.about).toBe('Finds data and establishes whether it can be trusted.');
  });

  it('leaves a description that is already short alone', () => {
    const [match] = openReferences('ask @', KNOWN).matches;
    expect(match.about).toBe('Finds data and says whether it can be trusted');
  });
});
