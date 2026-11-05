import { describe, expect, it } from 'vitest';

import { presentConfidence } from '@/lib/confidence-view';

const plain = {
  stance: 'plain' as const,
  hedge: '',
  concerns: [] as string[],
  whatWouldHelp: '',
};

describe('presentConfidence', () => {
  it('says nothing about a well-supported answer', () => {
    expect(presentConfidence(plain)).toBeNull();
  });

  it('leads with the main worry about a hedged answer', () => {
    const hedged = {
      ...plain,
      stance: 'hedged' as const,
      hedge: 'this rests on a single source',
      concerns: ['this rests on a single source'],
    };
    expect(presentConfidence(hedged)?.headline).toBe('Take this with some caution');
  });

  it('lists every worry', () => {
    const hedged = {
      ...plain,
      stance: 'hedged' as const,
      hedge: 'a; b',
      concerns: ['a', 'b'],
    };
    expect(presentConfidence(hedged)?.concerns).toEqual(['a', 'b']);
  });

  it('says plainly when it would rather not answer', () => {
    const declined = {
      stance: 'decline' as const,
      hedge: 'nothing was found to answer from',
      concerns: ['nothing was found to answer from'],
      whatWouldHelp: 'a source that speaks to this question',
    };
    expect(presentConfidence(declined)?.headline).toBe('Not enough to answer on');
  });

  it('says what would make the question answerable', () => {
    const declined = {
      stance: 'decline' as const,
      hedge: 'x',
      concerns: ['x'],
      whatWouldHelp: 'a source that speaks to this question',
    };
    expect(presentConfidence(declined)?.suggestion).toBe(
      'Would help: a source that speaks to this question',
    );
  });

  it('suggests nothing it cannot name', () => {
    const hedged = { ...plain, stance: 'hedged' as const, hedge: 'a', concerns: ['a'] };
    expect(presentConfidence(hedged)?.suggestion).toBe('');
  });

  it('shows a hedged answer rather than hiding it', () => {
    const hedged = { ...plain, stance: 'hedged' as const, hedge: 'a', concerns: ['a'] };
    expect(presentConfidence(hedged)?.showAnswer).toBe(true);
  });

  it('shows no answer it declined to stand behind', () => {
    const declined = { stance: 'decline' as const, hedge: 'a', concerns: ['a'], whatWouldHelp: 'b' };
    expect(presentConfidence(declined)?.showAnswer).toBe(false);
  });

  it('treats a hedge as worth noticing', () => {
    const hedged = { ...plain, stance: 'hedged' as const, hedge: 'a', concerns: ['a'] };
    expect(presentConfidence(hedged)?.severity).toBe('low');
  });

  it('treats a declined answer as worth real attention', () => {
    const declined = { stance: 'decline' as const, hedge: 'a', concerns: ['a'], whatWouldHelp: 'b' };
    expect(presentConfidence(declined)?.severity).toBe('medium');
  });
});
