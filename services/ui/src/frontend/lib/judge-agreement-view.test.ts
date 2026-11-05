import { describe, expect, it } from 'vitest';

import { presentAgreement } from '@/lib/judge-agreement-view';

const agreement = {
  agreement: 0.95,
  trust: 'reliable' as const,
  bias: '',
  tooGenerous: 1,
  tooHarsh: 0,
  disagreements: ['c3'],
  mayGate: true,
  reason: '',
  comparisons: 20,
};

describe('presentAgreement', () => {
  it('says how often the judge and people agree', () => {
    expect(presentAgreement(agreement).headline).toBe('Agrees with people 95% of the time');
  });

  it('says the judge can be relied on', () => {
    expect(presentAgreement(agreement).status).toBe('Reliable enough to gate releases');
  });

  it('says plainly when the judge cannot be relied on', () => {
    const poor = { ...agreement, agreement: 0.5, trust: 'unreliable' as const, mayGate: false };
    expect(presentAgreement(poor).status).toBe('Not reliable enough to gate releases');
  });

  it('says when there is not enough evidence yet', () => {
    const thin = {
      ...agreement,
      trust: 'unknown' as const,
      comparisons: 5,
      mayGate: false,
      reason: '20 comparisons are needed before trusting this judge',
    };
    expect(presentAgreement(thin).status).toBe('Not enough comparisons yet');
  });

  it('says how many more comparisons are needed', () => {
    const thin = {
      ...agreement,
      trust: 'unknown' as const,
      comparisons: 5,
      mayGate: false,
      reason: '20 comparisons are needed before trusting this judge',
    };
    expect(presentAgreement(thin).detail).toBe('20 comparisons are needed before trusting this judge');
  });

  it('describes a generous judge in plain words', () => {
    const generous = { ...agreement, bias: 'too generous', tooGenerous: 8 };
    expect(presentAgreement(generous).biasNote).toBe(
      'It passes things people would fail (8 times)',
    );
  });

  it('describes a harsh judge in plain words', () => {
    const harsh = { ...agreement, bias: 'too harsh', tooHarsh: 8, tooGenerous: 0 };
    expect(presentAgreement(harsh).biasNote).toBe('It fails things people would pass (8 times)');
  });

  it('says nothing about bias when there is none', () => {
    expect(presentAgreement({ ...agreement, bias: '' }).biasNote).toBe('');
  });

  it('links the cases they disagreed on', () => {
    expect(presentAgreement(agreement).openCases).toEqual(['c3']);
  });

  it('treats an unreliable judge as worth acting on', () => {
    const poor = { ...agreement, trust: 'unreliable' as const, mayGate: false };
    expect(presentAgreement(poor).severity).toBe('medium');
  });

  it('treats a reliable judge as unremarkable', () => {
    expect(presentAgreement(agreement).severity).toBe('none');
  });

  it('offers to review the disagreements', () => {
    expect(presentAgreement(agreement).action).toBe('review-disagreements');
  });

  it('offers more comparisons when there is not enough evidence', () => {
    const thin = { ...agreement, trust: 'unknown' as const, comparisons: 5, mayGate: false };
    expect(presentAgreement(thin).action).toBe('compare-more');
  });

  it('never says a judge is reliable while it cannot gate', () => {
    const poor = { ...agreement, trust: 'unreliable' as const, mayGate: false };
    expect(presentAgreement(poor).status.toLowerCase()).not.toBe('reliable enough to gate releases');
  });
});
