import { describe, expect, it } from 'vitest';

import { whenLastActive } from './when';

import en from '../i18n/locales/en.json';
import type { LastActive } from './when';

/**
 * `whenLastActive` describes rather than words: both the phrasing
 * and the date format belong to the reader's locale, and neither is
 * available out there. This mirrors what the component does, so the
 * assertions stay about the sentence a person reads.
 */
function said(when: LastActive, locale = 'en-GB'): string {
  switch (when.kind) {
    case 'unknown':
      return '';
    case 'justNow':
      return en.when.justNow;
    case 'ago': {
      const [, name] = when.key.split('.');
      const table = en.when as Record<string, string>;
      const form = table[`${name}_${when.count === 1 ? 'one' : 'other'}`];
      if (form === undefined) throw new Error(`no English string for '${when.key}'`);
      return form.replace('{{count}}', String(when.count));
    }
    default:
      return new Date(when.at).toLocaleDateString(locale, {
        day: 'numeric',
        month: 'long',
      });
  }
}


const NOW = new Date('2026-10-27T12:00:00Z');

describe('whenLastActive', () => {
  it('calls the last few minutes just now', () => {
    expect(said(whenLastActive('2026-10-27T11:59:10Z', NOW))).toBe('just now');
  });

  it('counts whole minutes', () => {
    expect(said(whenLastActive('2026-10-27T11:43:00Z', NOW))).toBe('17 minutes ago');
  });

  it('counts a single minute in the singular', () => {
    expect(said(whenLastActive('2026-10-27T11:58:30Z', NOW))).toBe('1 minute ago');
  });

  it('counts hours once minutes stop being useful', () => {
    expect(said(whenLastActive('2026-10-27T07:00:00Z', NOW))).toBe('5 hours ago');
  });

  it('counts days beyond a day', () => {
    expect(said(whenLastActive('2026-10-24T12:00:00Z', NOW))).toBe('3 days ago');
  });

  it('gives a date once it is weeks old, which is easier to place', () => {
    expect(said(whenLastActive('2026-09-01T12:00:00Z', NOW))).toBe('1 September');
  });

  it('says nothing about a conversation with no date', () => {
    expect(said(whenLastActive(null, NOW))).toBe('');
  });

  it('says nothing about a date it cannot read', () => {
    expect(said(whenLastActive('not a date', NOW))).toBe('');
  });

  it('does not claim a future date is old', () => {
    expect(said(whenLastActive('2026-10-27T12:05:00Z', NOW))).toBe('just now');
  });
});
