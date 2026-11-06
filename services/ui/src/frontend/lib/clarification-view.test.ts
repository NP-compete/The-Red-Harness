import { describe, expect, it } from 'vitest';

import { presentClarification } from '@/lib/clarification-view';

const asking = {
  ask: true,
  stop: false,
  question: 'which report: weekly or monthly?',
  options: ['weekly', 'monthly'],
  assuming: '',
  reason: '',
};

describe('presentClarification', () => {
  it('shows nothing when the run is proceeding without comment', () => {
    const clear = { ...asking, ask: false, question: '', options: [] };
    expect(presentClarification(clear)).toBeNull();
  });

  it('asks the question as given', () => {
    expect(presentClarification(asking)?.question).toBe('which report: weekly or monthly?');
  });

  it('offers each possibility as a choice', () => {
    expect(presentClarification(asking)?.choices).toEqual(['weekly', 'monthly']);
  });

  it('always allows an answer that is not on the list', () => {
    expect(presentClarification(asking)?.allowsFreeText).toBe(true);
  });

  it('says the run is waiting on the person', () => {
    expect(presentClarification(asking)?.state).toBe('waiting-for-you');
  });

  it('says plainly when the run went ahead on an assumption', () => {
    const assumed = { ...asking, ask: false, question: '', options: [], assuming: 'weekly' };
    expect(presentClarification(assumed)?.question).toBe('Assuming you meant weekly');
  });

  it('lets an assumption be corrected', () => {
    const assumed = { ...asking, ask: false, question: '', options: [], assuming: 'weekly' };
    expect(presentClarification(assumed)?.state).toBe('assumed');
  });

  it('does not block the run on an assumption', () => {
    const assumed = { ...asking, ask: false, question: '', options: [], assuming: 'weekly' };
    expect(presentClarification(assumed)?.blocking).toBe(false);
  });

  it('blocks the run while a question is open', () => {
    expect(presentClarification(asking)?.blocking).toBe(true);
  });

  it('says plainly when an unattended run stopped instead of guessing', () => {
    const stopped = {
      ...asking,
      ask: false,
      stop: true,
      question: '',
      options: [],
      reason: 'nobody is here to say which report',
    };
    expect(presentClarification(stopped)?.question).toBe(
      'This run stopped: nobody is here to say which report',
    );
  });

  it('offers to resume a stopped run with an answer', () => {
    const stopped = { ...asking, ask: false, stop: true, question: '', options: [], reason: 'x' };
    expect(presentClarification(stopped)?.state).toBe('stopped');
  });

  it('treats a stopped run as needing attention', () => {
    const stopped = { ...asking, ask: false, stop: true, question: '', options: [], reason: 'x' };
    expect(presentClarification(stopped)?.severity).toBe('medium');
  });

  it('treats an open question as routine', () => {
    expect(presentClarification(asking)?.severity).toBe('info');
  });

  it('treats an assumption as routine too', () => {
    const assumed = { ...asking, ask: false, question: '', options: [], assuming: 'weekly' };
    expect(presentClarification(assumed)?.severity).toBe('info');
  });
});
