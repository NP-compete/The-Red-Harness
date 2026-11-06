import { describe, expect, it } from 'vitest';

import { presentComparison } from '@/lib/eval-comparison-view';

const comparison = {
  verdict: 'regressed' as const,
  broken: ['case-a'],
  fixed: ['case-b', 'case-c'],
  beforeRate: 0.9,
  afterRate: 0.88,
  summary: '1 broke, 2 fixed',
  reason: '',
  beforeVersion: '4.1',
  afterVersion: '4.2',
};

describe('presentComparison', () => {
  it('leads with what broke rather than what improved', () => {
    expect(presentComparison(comparison).headline).toBe('1 case stopped working');
  });

  it('uses the plural when several broke', () => {
    const worse = { ...comparison, broken: ['a', 'b'] };
    expect(presentComparison(worse).headline).toBe('2 cases stopped working');
  });

  it('still mentions the improvements', () => {
    expect(presentComparison(comparison).detail).toBe('2 cases started working');
  });

  it('says plainly when nothing changed', () => {
    const same = {
      ...comparison,
      verdict: 'no-change' as const,
      broken: [],
      fixed: [],
      summary: 'nothing changed',
    };
    expect(presentComparison(same).headline).toBe('No change between 4.1 and 4.2');
  });

  it('celebrates an improvement with no regressions', () => {
    const better = { ...comparison, verdict: 'improved' as const, broken: [] };
    expect(presentComparison(better).headline).toBe('2 cases started working');
  });

  it('shows both pass rates', () => {
    expect(presentComparison(comparison).rates).toBe('90% → 88%');
  });

  it('blocks promotion when something regressed', () => {
    expect(presentComparison(comparison).canPromote).toBe(false);
  });

  it('allows promotion when nothing regressed', () => {
    const better = { ...comparison, verdict: 'improved' as const, broken: [] };
    expect(presentComparison(better).canPromote).toBe(true);
  });

  it('does not allow promotion on an inconclusive result', () => {
    const thin = {
      ...comparison,
      verdict: 'inconclusive' as const,
      broken: [],
      reason: '10 cases are needed before calling this an improvement',
    };
    expect(presentComparison(thin).canPromote).toBe(false);
  });

  it('explains why an inconclusive result is not enough', () => {
    const thin = {
      ...comparison,
      verdict: 'inconclusive' as const,
      broken: [],
      reason: '10 cases are needed before calling this an improvement',
    };
    expect(presentComparison(thin).detail).toBe(
      '10 cases are needed before calling this an improvement',
    );
  });

  it('links the broken cases so they can be opened', () => {
    expect(presentComparison(comparison).openCases).toEqual(['case-a']);
  });

  it('offers no cases to open when nothing broke', () => {
    const better = { ...comparison, verdict: 'improved' as const, broken: [] };
    expect(presentComparison(better).openCases).toEqual([]);
  });

  it('treats a regression as serious', () => {
    expect(presentComparison(comparison).severity).toBe('high');
  });

  it('treats an improvement as unremarkable', () => {
    const better = { ...comparison, verdict: 'improved' as const, broken: [] };
    expect(presentComparison(better).severity).toBe('none');
  });
});
