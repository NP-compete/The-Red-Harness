import { describe, expect, it } from 'vitest';

import { presentCaseProposal } from '@/lib/case-proposal-view';

const proposed = {
  proposed: true,
  question: 'What is the travel limit?',
  expected: '500 euros',
  fromRun: 'r1',
  needsReview: false,
  reason: '',
  duplicateOf: '',
};

describe('presentCaseProposal', () => {
  it('offers to add a case', () => {
    expect(presentCaseProposal(proposed)?.headline).toBe('Add this as a test case?');
  });

  it('shows the question the case would ask', () => {
    expect(presentCaseProposal(proposed)?.question).toBe('What is the travel limit?');
  });

  it('shows what the case would expect', () => {
    expect(presentCaseProposal(proposed)?.expected).toBe('Expected: 500 euros');
  });

  it('says nothing when no case could be made', () => {
    const refused = { ...proposed, proposed: false, reason: 'this could not be reproduced' };
    expect(presentCaseProposal(refused)).toBeNull();
  });

  it('points at the existing case when one already covers this', () => {
    const duplicate = {
      ...proposed,
      proposed: false,
      reason: 'the suite already asks this',
      duplicateOf: 'c0',
    };
    expect(presentCaseProposal(duplicate)?.headline).toBe('Already covered by c0');
  });

  it('offers to open the case that already covers it', () => {
    const duplicate = {
      ...proposed,
      proposed: false,
      reason: 'the suite already asks this',
      duplicateOf: 'c0',
    };
    expect(presentCaseProposal(duplicate)?.actions).toEqual(['Open c0']);
  });

  it('says when a case must be read before it joins the suite', () => {
    const personal = { ...proposed, needsReview: true };
    expect(presentCaseProposal(personal)?.note).toBe(
      'This mentions someone, so it needs a read before it is added',
    );
  });

  it('adds no note to an ordinary case', () => {
    expect(presentCaseProposal(proposed)?.note).toBe('');
  });

  it('makes adding the deliberate choice', () => {
    expect(presentCaseProposal(proposed)?.actions).toEqual(['Add case', 'Not this one']);
  });

  it('is an offer rather than an interruption', () => {
    expect(presentCaseProposal(proposed)?.blocking).toBe(false);
  });
});
