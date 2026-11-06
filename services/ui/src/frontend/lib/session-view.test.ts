import { describe, expect, it } from 'vitest';

import { presentSession } from '@/lib/session-view';

import en from '../i18n/locales/en.json';

/**
 * The module returns catalogue keys: it runs outside a component,
 * where there is no translator. Resolving through English keeps
 * each assertion about the sentence a person reads, and proves the
 * key and its plural forms exist.
 */
function said(key: string, count = 0): string {
  if (!key) return '';
  const [section, name] = key.split('.');
  const table = (en as Record<string, Record<string, string>>)[section] ?? {};
  const form = table[`${name}_${count === 1 ? 'one' : 'other'}`] ?? table[name];
  if (form === undefined) throw new Error(`no English string for '${key}'`);
  return form.replace('{{count}}', String(count));
}

const now = new Date('2026-10-27T09:00:00Z');

const live = {
  state: 'live' as const,
  usable: true,
  sessionStillValid: true,
  warn: false,
  idleAt: '2026-10-27T09:25:00Z',
  endsAt: '2026-10-27T19:00:00Z',
  reason: '',
  unsavedWork: false,
};

describe('presentSession', () => {
  it('shows nothing while the session is healthy', () => {
    expect(presentSession(live, now)).toBeNull();
  });

  it('warns shortly before an idle timeout', () => {
    const nearly = { ...live, warn: true, idleAt: '2026-10-27T09:02:00Z' };
    const soon = presentSession(nearly, now)!;
    expect(said(soon.headline, soon.headlineCount)).toBe('You will be signed out in 2 minutes');
  });

  it('offers a way to stay signed in', () => {
    const nearly = { ...live, warn: true, idleAt: '2026-10-27T09:02:00Z' };
    expect(presentSession(nearly, now)?.action).toBe('stay-signed-in');
  });

  it('says plainly when the session has ended', () => {
    const gone = {
      ...live,
      state: 'idle-expired' as const,
      usable: false,
      sessionStillValid: false,
      reason: 'this session has been idle too long',
    };
    expect(said(presentSession(gone, now)!.headline)).toBe('You have been signed out');
  });

  it('gives the reason the session ended', () => {
    const gone = {
      ...live,
      state: 'idle-expired' as const,
      usable: false,
      sessionStillValid: false,
      reason: 'this session has been idle too long',
    };
    expect(presentSession(gone, now)?.detail).toBe('this session has been idle too long');
  });

  it('asks for a sign-in again rather than treating it as a timeout', () => {
    const stepUp = {
      ...live,
      state: 'reauth-needed' as const,
      usable: false,
      reason: 'this action needs a recent sign-in',
    };
    expect(said(presentSession(stepUp, now)!.headline)).toBe('Confirm it is you to continue');
  });

  it('does not claim the person was signed out when only the action needs proof', () => {
    const stepUp = { ...live, state: 'reauth-needed' as const, usable: false, reason: 'x' };
    expect(presentSession(stepUp, now)?.signedOut).toBe(false);
  });

  it('says the person was signed out when they were', () => {
    const gone = {
      ...live,
      state: 'expired' as const,
      usable: false,
      sessionStillValid: false,
      reason: 'x',
    };
    expect(presentSession(gone, now)?.signedOut).toBe(true);
  });

  it('warns that unsaved work would be lost', () => {
    const nearly = { ...live, warn: true, idleAt: '2026-10-27T09:02:00Z', unsavedWork: true };
    expect(said(presentSession(nearly, now)!.detail)).toBe('You have unsaved work in this conversation');
  });

  it('says nothing about unsaved work when there is none', () => {
    const nearly = { ...live, warn: true, idleAt: '2026-10-27T09:02:00Z' };
    expect(presentSession(nearly, now)?.detail).toBe('');
  });

  it('treats an expiry warning as a warning', () => {
    const nearly = { ...live, warn: true, idleAt: '2026-10-27T09:02:00Z' };
    expect(presentSession(nearly, now)?.severity).toBe('medium');
  });

  it('treats being signed out as serious', () => {
    const gone = { ...live, state: 'expired' as const, usable: false, sessionStillValid: false, reason: 'x' };
    expect(presentSession(gone, now)?.severity).toBe('high');
  });

  it('cannot be dismissed once signed out', () => {
    const gone = { ...live, state: 'expired' as const, usable: false, sessionStillValid: false, reason: 'x' };
    expect(presentSession(gone, now)?.dismissible).toBe(false);
  });

  it('can be dismissed while it is only a warning', () => {
    const nearly = { ...live, warn: true, idleAt: '2026-10-27T09:02:00Z' };
    expect(presentSession(nearly, now)?.dismissible).toBe(true);
  });
});
