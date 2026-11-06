import { describe, expect, it } from 'vitest';

import { presentInterruption } from '@/lib/interrupt-view';

const folded = {
  handling: 'folded-in' as const,
  continues: true,
  keepsWork: true,
  appliesAfterCurrentStep: false,
  reason: '',
  tool: '',
};

describe('presentInterruption', () => {
  it('says an addition was taken on board', () => {
    expect(presentInterruption(folded).message).toBe('Added to what I am working on');
  });

  it('does not interrupt the view for an addition', () => {
    expect(presentInterruption(folded).interruptsReading).toBe(false);
  });

  it('says plainly when the work was redirected', () => {
    const redirected = {
      ...folded,
      handling: 'redirected' as const,
      keepsWork: false,
      reason: 'abandoning 2 steps of work',
    };
    expect(presentInterruption(redirected).message).toBe('Starting again: abandoning 2 steps of work');
  });

  it('warns that work is being thrown away', () => {
    const redirected = { ...folded, handling: 'redirected' as const, keepsWork: false, reason: 'x' };
    expect(presentInterruption(redirected).losesWork).toBe(true);
  });

  it('does not claim work is lost when it is kept', () => {
    expect(presentInterruption(folded).losesWork).toBe(false);
  });

  it('says plainly when the run was stopped', () => {
    const stopped = {
      ...folded,
      handling: 'stopped' as const,
      continues: false,
      keepsWork: false,
      reason: 'stopping after 2 steps',
    };
    expect(presentInterruption(stopped).message).toBe('Stopped: stopping after 2 steps');
  });

  it('says a step must finish before stopping takes effect', () => {
    const deferred = {
      ...folded,
      handling: 'stopped' as const,
      continues: false,
      keepsWork: false,
      appliesAfterCurrentStep: true,
      tool: 'send-email',
      reason: 'x',
    };
    expect(presentInterruption(deferred).pending).toBe('Waiting for send-email to finish first');
  });

  it('has nothing pending when it applies at once', () => {
    expect(presentInterruption(folded).pending).toBe('');
  });

  it('answers a question without implying the run changed', () => {
    const answered = { ...folded, handling: 'answered' as const };
    expect(presentInterruption(answered).message).toBe('Still working — here is where I am');
  });

  it('says plainly when the message arrived too late', () => {
    const late = {
      ...folded,
      handling: 'too-late' as const,
      continues: false,
      reason: 'this run had already finished',
    };
    expect(presentInterruption(late).message).toBe('This run had already finished');
  });

  it('shows nothing at all for a message that changed nothing', () => {
    const ignored = { ...folded, handling: 'ignored' as const };
    expect(presentInterruption(ignored).message).toBe('');
  });

  it('marks a stop as worth noticing', () => {
    const stopped = { ...folded, handling: 'stopped' as const, continues: false, reason: 'x' };
    expect(presentInterruption(stopped).interruptsReading).toBe(true);
  });

  it('marks a redirect as worth noticing', () => {
    const redirected = { ...folded, handling: 'redirected' as const, keepsWork: false, reason: 'x' };
    expect(presentInterruption(redirected).interruptsReading).toBe(true);
  });
});
