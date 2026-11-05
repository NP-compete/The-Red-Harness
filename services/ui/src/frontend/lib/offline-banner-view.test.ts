import { describe, expect, it } from 'vitest';

import { presentOfflineBanner } from '@/lib/offline-banner-view';

import en from '../i18n/locales/en.json';

/**
 * The module returns catalogue keys: it runs outside a component,
 * where there is no translator. Resolving through English keeps the
 * assertions about the sentence a person reads, and proves the key
 * and its plural forms exist.
 */
function said(key: string, count = 0): string {
  if (!key) return '';
  const [section, name] = key.split('.');
  const table = (en as Record<string, Record<string, string>>)[section] ?? {};
  const form = table[`${name}_${count === 1 ? 'one' : 'other'}`] ?? table[name];
  if (form === undefined) throw new Error(`no English string for '${key}'`);
  return form.replace('{{count}}', String(count));
}

const online = {
  connected: true,
  warn: false,
  queued: 0,
  runOutcomeUnknown: false,
  secondsDown: 0,
};

describe('presentOfflineBanner', () => {
  it('shows nothing while the connection is fine', () => {
    expect(presentOfflineBanner(online)).toBeNull();
  });

  it('shows nothing during a blip', () => {
    const blip = { ...online, connected: false, secondsDown: 2 };
    expect(presentOfflineBanner(blip)).toBeNull();
  });

  it('says plainly when the connection has gone', () => {
    const down = { ...online, connected: false, warn: true, secondsDown: 30 };
    expect(said(presentOfflineBanner(down)!.headline)).toBe('No connection');
  });

  it('says what is waiting to go out', () => {
    const down = { ...online, connected: false, warn: true, secondsDown: 30, queued: 2 };
    const two = presentOfflineBanner(down)!;
    expect(said(two.detail, two.queued)).toBe('2 messages will send when you are back');
  });

  it('counts one waiting message properly', () => {
    const down = { ...online, connected: false, warn: true, secondsDown: 30, queued: 1 };
    const one = presentOfflineBanner(down)!;
    expect(said(one.detail, one.queued)).toBe('1 message will send when you are back');
  });

  it('says nothing about a queue that is empty', () => {
    const down = { ...online, connected: false, warn: true, secondsDown: 30 };
    const none = presentOfflineBanner(down)!;
    expect(said(none.detail, none.queued)).toBe('');
  });

  it('is honest that a run in flight may have finished without us', () => {
    const down = {
      ...online,
      connected: false,
      warn: true,
      secondsDown: 30,
      runOutcomeUnknown: true,
    };
    expect(said(presentOfflineBanner(down)!.warning)).toBe(
      'A run was in progress — its outcome is unknown until you reconnect',
    );
  });

  it('adds no warning when nothing was running', () => {
    const down = { ...online, connected: false, warn: true, secondsDown: 30 };
    expect(said(presentOfflineBanner(down)!.warning)).toBe('');
  });

  it('offers a way to try again now', () => {
    const down = { ...online, connected: false, warn: true, secondsDown: 30 };
    expect(presentOfflineBanner(down)!.actions.map((k) => said(k))).toEqual(['Retry now']);
  });

  it('cannot be dismissed while the connection is down', () => {
    const down = { ...online, connected: false, warn: true, secondsDown: 30 };
    expect(presentOfflineBanner(down)!.dismissible).toBe(false);
  });

  it('treats an unknown run outcome as worth more attention', () => {
    const down = {
      ...online,
      connected: false,
      warn: true,
      secondsDown: 30,
      runOutcomeUnknown: true,
    };
    expect(presentOfflineBanner(down)!.severity).toBe('high');
  });

  it('treats a plain outage as worth noticing', () => {
    const down = { ...online, connected: false, warn: true, secondsDown: 30 };
    expect(presentOfflineBanner(down)!.severity).toBe('medium');
  });
});
