import { describe, expect, it } from 'vitest';

import { presentCallCheck } from '@/lib/tool-call-check-view';

const ok = {
  permitted: true,
  faults: [] as string[],
  retryable: false,
  reason: '',
  tool: 'send-email',
};

describe('presentCallCheck', () => {
  it('shows nothing when the call is sound', () => {
    expect(presentCallCheck(ok)).toBeNull();
  });

  it('says plainly when a call was stopped', () => {
    const blocked = {
      ...ok,
      permitted: false,
      faults: ['server-untrusted'],
      reason: 'send-email: the server is not the one that was trusted',
    };
    expect(presentCallCheck(blocked)?.headline).toBe('send-email was not run');
  });

  it('gives the reason it was stopped', () => {
    const blocked = {
      ...ok,
      permitted: false,
      faults: ['server-untrusted'],
      reason: 'send-email: the server is not the one that was trusted',
    };
    expect(presentCallCheck(blocked)?.detail).toBe(
      'send-email: the server is not the one that was trusted',
    );
  });

  it('describes each fault in plain words', () => {
    const blocked = {
      ...ok,
      permitted: false,
      faults: ['no-credential', 'destination-blocked'],
      reason: 'x',
    };
    expect(presentCallCheck(blocked)?.problems).toEqual([
      'There is no credential set up for this',
      'That address is not one this agent may reach',
    ]);
  });

  it('says a waitable problem will clear on its own', () => {
    const busy = { ...ok, permitted: false, faults: ['rate-limited'], retryable: true, reason: 'x' };
    expect(presentCallCheck(busy)?.willRetry).toBe(true);
  });

  it('does not promise a retry for a broken call', () => {
    const broken = { ...ok, permitted: false, faults: ['bad-arguments'], reason: 'x' };
    expect(presentCallCheck(broken)?.willRetry).toBe(false);
  });

  it('treats a trust problem as the most serious', () => {
    const blocked = { ...ok, permitted: false, faults: ['server-untrusted'], reason: 'x' };
    expect(presentCallCheck(blocked)?.severity).toBe('high');
  });

  it('treats a changed tool as serious too', () => {
    const blocked = { ...ok, permitted: false, faults: ['shape-changed'], reason: 'x' };
    expect(presentCallCheck(blocked)?.severity).toBe('high');
  });

  it('treats waiting as routine', () => {
    const busy = { ...ok, permitted: false, faults: ['rate-limited'], retryable: true, reason: 'x' };
    expect(presentCallCheck(busy)?.severity).toBe('info');
  });

  it('treats a fixable call as worth a look', () => {
    const broken = { ...ok, permitted: false, faults: ['bad-arguments'], reason: 'x' };
    expect(presentCallCheck(broken)?.severity).toBe('medium');
  });

  it('offers to review the connection for a trust problem', () => {
    const blocked = { ...ok, permitted: false, faults: ['server-untrusted'], reason: 'x' };
    expect(presentCallCheck(blocked)?.action).toBe('review-connection');
  });

  it('offers nothing to do while waiting', () => {
    const busy = { ...ok, permitted: false, faults: ['rate-limited'], retryable: true, reason: 'x' };
    expect(presentCallCheck(busy)?.action).toBe('none');
  });

  it('never suggests the call went through', () => {
    const blocked = { ...ok, permitted: false, faults: ['server-untrusted'], reason: 'x' };
    expect(presentCallCheck(blocked)?.ran).toBe(false);
  });
});
