import { describe, expect, it } from 'vitest';

import { presentReference } from '@/lib/reference-view';

const resolved = {
  entity: 'report-7',
  resolved: true,
  shouldAsk: false,
  candidates: [] as string[],
};

describe('presentReference', () => {
  it('says nothing when the question named its own subject', () => {
    const named = { ...resolved, entity: null, resolved: false };
    expect(presentReference(named)).toBeNull();
  });

  it('shows what it took a bare reference to mean', () => {
    expect(presentReference(resolved)?.note).toBe('Taking “it” to mean report-7');
  });

  it('offers a way to correct a wrong guess', () => {
    expect(presentReference(resolved)?.action).toBe('Not that one');
  });

  it('asks rather than guessing between two things', () => {
    const torn = {
      entity: null,
      resolved: false,
      shouldAsk: true,
      candidates: ['report-7', 'report-9'],
    };
    expect(presentReference(torn)?.note).toBe('Which one did you mean?');
  });

  it('offers both things it was torn between', () => {
    const torn = {
      entity: null,
      resolved: false,
      shouldAsk: true,
      candidates: ['report-7', 'report-9'],
    };
    expect(presentReference(torn)?.choices).toEqual(['report-7', 'report-9']);
  });

  it('asks plainly when it has nothing to point at', () => {
    const lost = { entity: null, resolved: false, shouldAsk: true, candidates: [] };
    expect(presentReference(lost)?.note).toBe('What should this apply to?');
  });

  it('offers no choices when it has none', () => {
    const lost = { entity: null, resolved: false, shouldAsk: true, candidates: [] };
    expect(presentReference(lost)?.choices).toEqual([]);
  });

  it('waits for an answer when it had to ask', () => {
    const lost = { entity: null, resolved: false, shouldAsk: true, candidates: [] };
    expect(presentReference(lost)?.blocking).toBe(true);
  });

  it('carries on when it was confident', () => {
    expect(presentReference(resolved)?.blocking).toBe(false);
  });

  it('offers nothing to correct when it is already asking', () => {
    const lost = { entity: null, resolved: false, shouldAsk: true, candidates: [] };
    expect(presentReference(lost)?.action).toBe('');
  });
});
