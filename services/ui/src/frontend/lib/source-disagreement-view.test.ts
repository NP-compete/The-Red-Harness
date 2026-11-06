import { describe, expect, it } from 'vitest';

import { presentDisagreement } from '@/lib/source-disagreement-view';

const agreed = {
  disagree: false,
  answers: ['500'],
  byAnswer: { '500': ['handbook', 'policy'] },
  preferred: '500',
  showBoth: false,
  reason: '',
};

const split = {
  disagree: true,
  answers: ['1000', '500'],
  byAnswer: { '500': ['handbook'], '1000': ['policy'] },
  preferred: '1000',
  showBoth: true,
  reason: 'this comes from a policy, which outranks the others',
};

describe('presentDisagreement', () => {
  it('shows nothing when the sources agree', () => {
    expect(presentDisagreement(agreed)).toBeNull();
  });

  it('says plainly that the sources disagree', () => {
    expect(presentDisagreement(split)?.headline).toBe('Sources disagree on this');
  });

  it('shows each answer with who says it', () => {
    expect(presentDisagreement(split)?.options).toEqual([
      { answer: '1000', sources: ['policy'], preferred: true },
      { answer: '500', sources: ['handbook'], preferred: false },
    ]);
  });

  it('puts the preferred answer first', () => {
    expect(presentDisagreement(split)?.options[0].answer).toBe('1000');
  });

  it('explains why one answer is preferred', () => {
    expect(presentDisagreement(split)?.detail).toBe(
      'this comes from a policy, which outranks the others',
    );
  });

  it('says plainly when neither answer can be preferred', () => {
    const undecided = {
      ...split,
      preferred: '',
      reason: 'the sources disagree and nothing marks one as better',
    };
    expect(presentDisagreement(undecided)?.detail).toBe(
      'the sources disagree and nothing marks one as better',
    );
  });

  it('marks nothing as preferred when nothing is', () => {
    const undecided = { ...split, preferred: '', reason: 'x' };
    expect(presentDisagreement(undecided)?.options.every((o) => !o.preferred)).toBe(true);
  });

  it('keeps an undecided disagreement in a stable order', () => {
    const undecided = { ...split, preferred: '', reason: 'x' };
    expect(presentDisagreement(undecided)?.options.map((o) => o.answer)).toEqual(['1000', '500']);
  });

  it('treats an undecided disagreement as more serious', () => {
    const undecided = { ...split, preferred: '', reason: 'x' };
    expect(presentDisagreement(undecided)?.severity).toBe('high');
  });

  it('treats a resolved disagreement as a caution', () => {
    expect(presentDisagreement(split)?.severity).toBe('medium');
  });

  it('never hides the losing answer', () => {
    expect(presentDisagreement(split)?.options).toHaveLength(2);
  });

  it('offers to open the sources', () => {
    expect(presentDisagreement(split)?.action).toBe('compare-sources');
  });

  it('cannot be dismissed while the answer is in doubt', () => {
    const undecided = { ...split, preferred: '', reason: 'x' };
    expect(presentDisagreement(undecided)?.dismissible).toBe(false);
  });

  it('can be dismissed once one answer is preferred', () => {
    expect(presentDisagreement(split)?.dismissible).toBe(true);
  });
});
