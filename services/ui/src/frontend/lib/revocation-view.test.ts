import { describe, expect, it } from 'vitest';

import { presentRevocation } from '@/lib/revocation-view';

const valid = {
  verdict: 'valid' as const,
  mustSignInAgain: false,
  reason: '',
  wasThisDevice: true,
  otherSessionsEnded: 0,
};

describe('presentRevocation', () => {
  it('shows nothing while the session is good', () => {
    expect(presentRevocation(valid)).toBeNull();
  });

  it('says plainly when the session was ended', () => {
    const ended = {
      ...valid,
      verdict: 'revoked' as const,
      mustSignInAgain: true,
      reason: 'password changed',
    };
    expect(presentRevocation(ended)?.headline).toBe('You have been signed out');
  });

  it('gives the reason it was ended', () => {
    const ended = {
      ...valid,
      verdict: 'revoked' as const,
      mustSignInAgain: true,
      reason: 'password changed',
    };
    expect(presentRevocation(ended)?.detail).toBe('password changed');
  });

  it('says plainly when someone else ended it', () => {
    const ended = {
      ...valid,
      verdict: 'revoked' as const,
      mustSignInAgain: true,
      reason: 'lost laptop',
      wasThisDevice: false,
    };
    expect(presentRevocation(ended)?.detail).toBe('lost laptop');
  });

  it('offers a way back in', () => {
    const ended = { ...valid, verdict: 'revoked' as const, mustSignInAgain: true, reason: 'x' };
    expect(presentRevocation(ended)?.action).toBe('sign-in');
  });

  it('treats being signed out as serious', () => {
    const ended = { ...valid, verdict: 'revoked' as const, mustSignInAgain: true, reason: 'x' };
    expect(presentRevocation(ended)?.severity).toBe('high');
  });

  it('cannot be dismissed', () => {
    const ended = { ...valid, verdict: 'revoked' as const, mustSignInAgain: true, reason: 'x' };
    expect(presentRevocation(ended)?.dismissible).toBe(false);
  });

  it('confirms how many other sessions were ended', () => {
    const swept = { ...valid, otherSessionsEnded: 3 };
    expect(presentRevocation(swept)?.headline).toBe('Signed out of 3 other places');
  });

  it('uses the singular for one other session', () => {
    const swept = { ...valid, otherSessionsEnded: 1 };
    expect(presentRevocation(swept)?.headline).toBe('Signed out of 1 other place');
  });

  it('treats a successful sweep as reassuring, not alarming', () => {
    const swept = { ...valid, otherSessionsEnded: 3 };
    expect(presentRevocation(swept)?.severity).toBe('info');
  });

  it('lets a sweep confirmation be dismissed', () => {
    const swept = { ...valid, otherSessionsEnded: 3 };
    expect(presentRevocation(swept)?.dismissible).toBe(true);
  });

  it('offers nothing to do after a sweep', () => {
    const swept = { ...valid, otherSessionsEnded: 3 };
    expect(presentRevocation(swept)?.action).toBe('none');
  });

  it('never claims the session still works once revoked', () => {
    const ended = { ...valid, verdict: 'revoked' as const, mustSignInAgain: true, reason: 'x' };
    expect(presentRevocation(ended)?.stillSignedIn).toBe(false);
  });
});
