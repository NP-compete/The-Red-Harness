import { describe, expect, it } from 'vitest';

import { presentGrounding } from '@/lib/grounding-view';

const grounded = {
  grounded: true,
  supportedShare: 1,
  unsupported: [] as string[],
  claims: [
    { text: 'Expenses over 500 need approval.', supported: true, supportedBy: 'handbook', reason: '' },
  ],
  reason: '',
};

describe('presentGrounding', () => {
  it('shows nothing when every claim is backed up', () => {
    expect(presentGrounding(grounded)).toBeNull();
  });

  it('says plainly when part of the answer is unsupported', () => {
    const partial = {
      ...grounded,
      grounded: false,
      supportedShare: 0.5,
      unsupported: ['Reimbursement takes three days.'],
      claims: [
        ...grounded.claims,
        {
          text: 'Reimbursement takes three days.',
          supported: false,
          supportedBy: '',
          reason: 'the cited passages do not say this',
        },
      ],
    };
    expect(presentGrounding(partial)?.headline).toBe('1 part of this answer is not backed by a source');
  });

  it('uses the plural for several unsupported claims', () => {
    const partial = {
      ...grounded,
      grounded: false,
      supportedShare: 0,
      unsupported: ['a', 'b'],
      claims: [],
    };
    expect(presentGrounding(partial)?.headline).toBe(
      '2 parts of this answer are not backed by a source',
    );
  });

  it('lists the unsupported parts so they can be checked', () => {
    const partial = { ...grounded, grounded: false, unsupported: ['a', 'b'], claims: [] };
    expect(presentGrounding(partial)?.parts).toEqual(['a', 'b']);
  });

  it('says plainly when nothing could be checked at all', () => {
    const empty = {
      ...grounded,
      grounded: false,
      supportedShare: 0,
      claims: [],
      unsupported: [],
      reason: 'there was nothing in the answer to check',
    };
    expect(presentGrounding(empty)?.headline).toBe('This answer could not be checked');
  });

  it('treats an entirely unsupported answer as serious', () => {
    const none = { ...grounded, grounded: false, supportedShare: 0, unsupported: ['a'], claims: [] };
    expect(presentGrounding(none)?.severity).toBe('high');
  });

  it('treats a mostly supported answer as a caution', () => {
    const mostly = {
      ...grounded,
      grounded: false,
      supportedShare: 0.8,
      unsupported: ['a'],
      claims: [],
    };
    expect(presentGrounding(mostly)?.severity).toBe('medium');
  });

  it('never presents an unsupported answer as verified', () => {
    const none = { ...grounded, grounded: false, supportedShare: 0, unsupported: ['a'], claims: [] };
    expect(presentGrounding(none)?.verified).toBe(false);
  });

  it('offers to see the sources that were read', () => {
    const partial = { ...grounded, grounded: false, unsupported: ['a'], claims: [] };
    expect(presentGrounding(partial)?.action).toBe('show-sources');
  });

  it('says how much of the answer is supported', () => {
    const partial = { ...grounded, grounded: false, supportedShare: 0.5, unsupported: ['a'], claims: [] };
    expect(presentGrounding(partial)?.detail).toBe('50% of this answer is backed by a source');
  });

  it('does not claim a percentage when nothing was checked', () => {
    const empty = {
      ...grounded,
      grounded: false,
      supportedShare: 0,
      claims: [],
      unsupported: [],
      reason: 'there was nothing in the answer to check',
    };
    expect(presentGrounding(empty)?.detail).toBe('there was nothing in the answer to check');
  });
});

describe('presentGrounding with contradictions', () => {
  const contradicted = {
    grounded: false,
    supportedShare: 0.5,
    unsupported: ['Expenses over 500 do not need approval.'],
    contradicted: ['Expenses over 500 do not need approval.'],
    claims: [],
    reason: '',
  };

  it('leads with the contradiction rather than the missing support', () => {
    expect(presentGrounding(contradicted)?.headline).toBe(
      '1 part of this answer contradicts its source',
    );
  });

  it('is always serious, however much else is supported', () => {
    expect(presentGrounding({ ...contradicted, supportedShare: 0.95 })?.severity).toBe('high');
  });

  it('lists the contradicting parts separately', () => {
    expect(presentGrounding(contradicted)?.contradictions).toEqual([
      'Expenses over 500 do not need approval.',
    ]);
  });

  it('does not count a contradiction twice as merely unsupported', () => {
    expect(presentGrounding(contradicted)?.parts).toEqual([]);
  });

  it('has no contradictions listed when there are none', () => {
    const plain = { ...contradicted, contradicted: [] };
    expect(presentGrounding(plain)?.contradictions).toEqual([]);
  });
});
