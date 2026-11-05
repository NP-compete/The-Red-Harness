import { describe, expect, it } from 'vitest';

import { presentSideEffects } from '@/lib/side-effects-view';

const effects = {
  count: 3,
  changedAnything: true,
  byKind: {
    'file-written': ['out/a.md', 'out/b.md'],
    'email-sent': ['ana'],
  },
  permanent: ['email-sent: ana'],
  fullyReversible: false,
  undoSteps: ['delete the file'],
  cost: '1.75',
  currency: 'USD',
  summary: '2 files written, 1 email sent',
};

describe('presentSideEffects', () => {
  it('says plainly when nothing was changed', () => {
    const none = {
      ...effects,
      count: 0,
      changedAnything: false,
      byKind: {},
      permanent: [],
      fullyReversible: true,
      undoSteps: [],
      summary: 'Nothing was changed',
    };
    expect(presentSideEffects(none).headline).toBe('Nothing was changed');
  });

  it('shows the summary it was given', () => {
    expect(presentSideEffects(effects).headline).toBe('2 files written, 1 email sent');
  });

  it('lists each kind of change with what it touched', () => {
    expect(presentSideEffects(effects).groups).toEqual([
      { label: 'Files written', targets: ['out/a.md', 'out/b.md'] },
      { label: 'Emails sent', targets: ['ana'] },
    ]);
  });

  it('shows what cannot be taken back', () => {
    expect(presentSideEffects(effects).permanent).toEqual(['email-sent: ana']);
  });

  it('says plainly that the run cannot be fully undone', () => {
    expect(presentSideEffects(effects).undoNote).toBe('Some of this cannot be undone');
  });

  it('offers to undo when everything can be reversed', () => {
    const clean = { ...effects, permanent: [], fullyReversible: true };
    expect(presentSideEffects(clean).action).toBe('undo');
  });

  it('offers no undo button when part of it is permanent', () => {
    expect(presentSideEffects(effects).action).toBe('none');
  });

  it('still shows the steps to undo what can be undone', () => {
    expect(presentSideEffects(effects).undoSteps).toEqual(['delete the file']);
  });

  it('shows what the run cost', () => {
    expect(presentSideEffects(effects).cost).toBe('$1.75');
  });

  it('shows nothing for a run that cost nothing', () => {
    expect(presentSideEffects({ ...effects, cost: '0.00' }).cost).toBe('');
  });

  it('treats permanent changes as worth reading carefully', () => {
    expect(presentSideEffects(effects).severity).toBe('medium');
  });

  it('treats a fully reversible run as routine', () => {
    const clean = { ...effects, permanent: [], fullyReversible: true };
    expect(presentSideEffects(clean).severity).toBe('info');
  });

  it('shows no groups when nothing changed', () => {
    const none = { ...effects, count: 0, changedAnything: false, byKind: {} };
    expect(presentSideEffects(none).groups).toEqual([]);
  });
});
