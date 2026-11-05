import { describe, expect, it } from 'vitest';

import { presentAnswer } from '@/lib/answer-sections-view';

const assembled = {
  sections: [
    {
      question: 'what is the expense limit',
      text: 'The limit is 500.',
      sources: ['handbook'],
      answered: true,
      unsourced: false,
    },
    {
      question: 'who approves it',
      text: 'No answer was found for this.',
      sources: [] as string[],
      answered: false,
      unsourced: false,
    },
  ],
  allSources: ['handbook'],
  complete: false,
  useHeadings: true,
};

describe('presentAnswer', () => {
  it('shows a heading for each part when there are several', () => {
    expect(presentAnswer(assembled).blocks[0].heading).toBe('What is the expense limit');
  });

  it('shows no heading for a single-part answer', () => {
    const single = { ...assembled, sections: [assembled.sections[0]], useHeadings: true };
    expect(presentAnswer({ ...single, useHeadings: false }).blocks[0].heading).toBe('');
  });

  it('shows the answer text', () => {
    expect(presentAnswer(assembled).blocks[0].text).toBe('The limit is 500.');
  });

  it('shows each section’s sources', () => {
    expect(presentAnswer(assembled).blocks[0].sources).toEqual(['handbook']);
  });

  it('marks a gap so it is not read as an answer', () => {
    expect(presentAnswer(assembled).blocks[1].state).toBe('missing');
  });

  it('marks an ordinary section as answered', () => {
    expect(presentAnswer(assembled).blocks[0].state).toBe('answered');
  });

  it('marks an unsourced section differently from a gap', () => {
    const loose = {
      ...assembled,
      sections: [{ ...assembled.sections[0], sources: [], unsourced: true }],
    };
    expect(presentAnswer(loose).blocks[0].state).toBe('unsourced');
  });

  it('warns when part of the answer is missing', () => {
    expect(presentAnswer(assembled).warning).toBe('1 part of your question is unanswered');
  });

  it('does not warn about a complete answer', () => {
    const whole = {
      ...assembled,
      sections: [assembled.sections[0]],
      complete: true,
      useHeadings: false,
    };
    expect(presentAnswer(whole).warning).toBe('');
  });

  it('lists every source used once, at the end', () => {
    expect(presentAnswer(assembled).sources).toEqual(['handbook']);
  });

  it('says plainly when nothing was sourced at all', () => {
    const loose = { ...assembled, allSources: [] };
    expect(presentAnswer(loose).sources).toEqual([]);
  });

  it('counts how much of the answer stands on sources', () => {
    expect(presentAnswer(assembled).sourcedShare).toBe('1 of 2 parts have sources');
  });

  it('offers to search again for a missing part', () => {
    expect(presentAnswer(assembled).action).toBe('search-again');
  });

  it('offers nothing when the answer is whole', () => {
    const whole = { ...assembled, sections: [assembled.sections[0]], complete: true };
    expect(presentAnswer(whole).action).toBe('none');
  });
});
