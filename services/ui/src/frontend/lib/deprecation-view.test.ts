import { describe, expect, it } from 'vitest';

import { presentDeprecation } from '@/lib/deprecation-view';

const status = {
  tool: 'send-email',
  stage: 'deprecated' as const,
  usable: true,
  replacement: 'send-message',
  daysLeft: 35,
  message: 'send-email will be removed on 1 December 2026; use send-message instead',
};

describe('presentDeprecation', () => {
  it('shows nothing for a current tool', () => {
    const current = { ...status, stage: 'current' as const, daysLeft: 0, message: '' };
    expect(presentDeprecation(current)).toBeNull();
  });

  it('says a deprecated tool still works', () => {
    expect(presentDeprecation(status)?.stillWorks).toBe(true);
  });

  it('shows the notice it was given', () => {
    expect(presentDeprecation(status)?.message).toBe(status.message);
  });

  it('says how long is left in weeks when it is far off', () => {
    expect(presentDeprecation(status)?.timeLeft).toBe('5 weeks left');
  });

  it('counts down in days when it is close', () => {
    expect(presentDeprecation({ ...status, daysLeft: 6 })?.timeLeft).toBe('6 days left');
  });

  it('is quiet about a distant removal', () => {
    expect(presentDeprecation(status)?.severity).toBe('low');
  });

  it('gets louder as removal approaches', () => {
    expect(presentDeprecation({ ...status, daysLeft: 6 })?.severity).toBe('medium');
  });

  it('is loudest once the tool is gone', () => {
    const gone = { ...status, stage: 'removed' as const, usable: false, daysLeft: 0 };
    expect(presentDeprecation(gone)?.severity).toBe('high');
  });

  it('says a removed tool no longer works', () => {
    const gone = { ...status, stage: 'removed' as const, usable: false, daysLeft: 0 };
    expect(presentDeprecation(gone)?.stillWorks).toBe(false);
  });

  it('offers to switch to the replacement', () => {
    expect(presentDeprecation(status)?.action).toBe('switch');
  });

  it('offers nothing to switch to when there is no replacement', () => {
    const orphan = { ...status, replacement: '' };
    expect(presentDeprecation(orphan)?.action).toBe('none');
  });

  it('names the replacement separately so it can be linked', () => {
    expect(presentDeprecation(status)?.replacement).toBe('send-message');
  });

  it('says what to do when a removed tool has no replacement', () => {
    const stranded = {
      ...status,
      stage: 'removed' as const,
      usable: false,
      replacement: '',
      daysLeft: 0,
    };
    expect(presentDeprecation(stranded)?.action).toBe('contact-admin');
  });
});
