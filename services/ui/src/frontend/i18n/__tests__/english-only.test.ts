import { readdirSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import i18n, { LANGUAGES } from '../index';

/**
 * One language, and the catalogue kept.
 *
 * The product no longer offers a choice of language. What stays is
 * the catalogue: strings live in `en.json` rather than scattered
 * through 94 components, so they can still be found, reviewed and
 * changed in one place.
 *
 * These tests exist so "English only" does not quietly drift back
 * into a half-supported second language — a locale file nobody
 * maintains is worse than none, because it renders stale text to
 * somebody who cannot tell it is stale.
 */

const LOCALES = join(__dirname, '..', 'locales');

describe('one language', () => {
  it('ships exactly one catalogue', () => {
    const files = readdirSync(LOCALES).filter((f) => f.endsWith('.json'));
    expect(files).toEqual(['en.json']);
  });

  it('offers no choice of language', () => {
    expect(LANGUAGES.map((l) => l.code)).toEqual(['en']);
  });

  it('resolves to English', () => {
    expect(i18n.resolvedLanguage ?? i18n.language).toMatch(/^en/);
  });

  it('knows about no other language', () => {
    expect(Object.keys(i18n.options.resources ?? {})).toEqual(['en']);
  });
});

describe('the catalogue still works', () => {
  it('returns the English string for a key', () => {
    expect(i18n.t('common.cancel')).not.toBe('common.cancel');
  });

  it('interpolates', () => {
    const found = i18n.t('library.used', { used: '1 KB', limit: '10 KB' });
    expect(found).toContain('1 KB');
  });

  it('returns the key when there is no string, rather than blank', () => {
    // Blank is invisible in the interface; the key is at least a
    // thing somebody can search for.
    expect(i18n.t('nothing.like.this')).toBe('nothing.like.this');
  });
});

describe('the browser no longer decides', () => {
  it('does not consult the browser or storage for a language', () => {
    // Detection only made sense when there was something to
    // detect. Leaving it in would let a stale localStorage value
    // select a language that no longer exists.
    expect(i18n.options.detection).toBeUndefined();
  });
});
