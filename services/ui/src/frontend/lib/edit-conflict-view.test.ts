import { describe, expect, it } from 'vitest';

import { presentEditOutcome } from '@/lib/edit-conflict-view';

const applied = {
  outcome: 'applied' as const,
  version: 8,
  reason: '',
  disputed: [] as string[],
  otherAuthor: '',
};

describe('presentEditOutcome', () => {
  it('confirms a saved change quietly', () => {
    const shown = presentEditOutcome(applied);
    expect(shown.headline).toBe('Saved');
    expect(shown.severity).toBe('none');
  });

  it('says when a change was merged with someone elses', () => {
    const merged = { ...applied, outcome: 'merged' as const, otherAuthor: 'bo' };
    expect(presentEditOutcome(merged).headline).toBe('Saved alongside changes from bo');
  });

  it('treats a merge as worth noticing but not a problem', () => {
    const merged = { ...applied, outcome: 'merged' as const, otherAuthor: 'bo' };
    expect(presentEditOutcome(merged).severity).toBe('low');
  });

  it('says plainly when a change was not saved', () => {
    const conflict = {
      ...applied,
      outcome: 'conflict' as const,
      version: 7,
      disputed: ['model'],
      otherAuthor: 'bo',
      reason: 'someone else changed model first',
    };
    expect(presentEditOutcome(conflict).headline).toBe('Not saved — bo changed model first');
  });

  it('names every disputed setting', () => {
    const conflict = {
      ...applied,
      outcome: 'conflict' as const,
      disputed: ['model', 'budget'],
      otherAuthor: 'bo',
      reason: 'x',
    };
    expect(presentEditOutcome(conflict).headline).toBe(
      'Not saved — bo changed model and budget first',
    );
  });

  it('treats a conflict as serious', () => {
    const conflict = { ...applied, outcome: 'conflict' as const, disputed: ['model'], reason: 'x' };
    expect(presentEditOutcome(conflict).severity).toBe('high');
  });

  it('offers to look at the difference before choosing', () => {
    const conflict = { ...applied, outcome: 'conflict' as const, disputed: ['model'], reason: 'x' };
    expect(presentEditOutcome(conflict).action).toBe('compare');
  });

  it('never offers to overwrite without looking first', () => {
    const conflict = { ...applied, outcome: 'conflict' as const, disputed: ['model'], reason: 'x' };
    expect(presentEditOutcome(conflict).action).not.toBe('overwrite');
  });

  it('says nothing needed saving when nothing changed', () => {
    const none = { ...applied, outcome: 'no-change' as const, version: 7 };
    expect(presentEditOutcome(none).headline).toBe('Nothing to save');
  });

  it('asks for a reload when the version is not recognised', () => {
    const unknown = { ...applied, outcome: 'unknown-version' as const, reason: 'x' };
    expect(presentEditOutcome(unknown).action).toBe('reload');
  });

  it('explains an unrecognised version without jargon', () => {
    const unknown = { ...applied, outcome: 'unknown-version' as const, reason: 'x' };
    expect(presentEditOutcome(unknown).headline).toBe(
      'This page is out of date — reload before saving',
    );
  });

  it('says whether the editor should keep the users text', () => {
    const conflict = { ...applied, outcome: 'conflict' as const, disputed: ['model'], reason: 'x' };
    expect(presentEditOutcome(conflict).keepDraft).toBe(true);
  });

  it('lets the editor clear once the change is saved', () => {
    expect(presentEditOutcome(applied).keepDraft).toBe(false);
  });
});
