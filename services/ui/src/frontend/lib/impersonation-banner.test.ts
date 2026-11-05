import { describe, expect, it } from 'vitest';

import { presentImpersonation } from '@/lib/impersonation-banner';

const now = new Date('2026-10-27T09:00:00Z');

const session = {
  actingAs: 'ana',
  really: 'cy',
  expiresAt: '2026-10-27T12:00:00Z',
  readOnly: true,
  reason: 'investigating a failed run reported by the user',
};

describe('presentImpersonation', () => {
  it('shows nothing when nobody is being impersonated', () => {
    expect(presentImpersonation(null, now)).toBeNull();
  });

  it('says who is being acted as', () => {
    expect(presentImpersonation(session, now)?.headline).toBe('You are acting as ana');
  });

  it('says the session is read only', () => {
    expect(presentImpersonation(session, now)?.scope).toBe('read only');
  });

  it('says plainly when the session can change things', () => {
    const writable = { ...session, readOnly: false };
    expect(presentImpersonation(writable, now)?.scope).toBe('can make changes');
  });

  it('treats a writable session as more serious', () => {
    const writable = { ...session, readOnly: false };
    expect(presentImpersonation(writable, now)?.severity).toBe('high');
  });

  it('treats a read-only session as less serious but still visible', () => {
    expect(presentImpersonation(session, now)?.severity).toBe('medium');
  });

  it('says how long is left', () => {
    expect(presentImpersonation(session, now)?.timeLeft).toBe('3 hours left');
  });

  it('counts down in minutes near the end', () => {
    const nearly = { ...session, expiresAt: '2026-10-27T09:12:00Z' };
    expect(presentImpersonation(nearly, now)?.timeLeft).toBe('12 minutes left');
  });

  it('says an expired session has ended rather than showing a negative time', () => {
    const over = { ...session, expiresAt: '2026-10-27T08:00:00Z' };
    expect(presentImpersonation(over, now)?.timeLeft).toBe('ended');
  });

  it('says an expired session is no longer active', () => {
    const over = { ...session, expiresAt: '2026-10-27T08:00:00Z' };
    expect(presentImpersonation(over, now)?.active).toBe(false);
  });

  it('always offers a way out', () => {
    expect(presentImpersonation(session, now)?.action).toBe('stop');
  });

  it('shows the reason so the record is visible to the person using it', () => {
    expect(presentImpersonation(session, now)?.reason).toBe(
      'investigating a failed run reported by the user',
    );
  });

  it('cannot be dismissed', () => {
    expect(presentImpersonation(session, now)?.dismissible).toBe(false);
  });
});
