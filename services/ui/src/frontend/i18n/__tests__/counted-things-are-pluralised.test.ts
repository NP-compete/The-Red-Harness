import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

/**
 * "1 days".
 *
 * I18N-3 asks that interpolated counts use plural forms. The
 * catalogue mostly did — 104 keys interpolated `{{count}}` and
 * 97 of them carried `_one` and `_other` — and nothing checked,
 * so the other seven had gone unnoticed. Four were real:
 *
 *     share.days             "{{count}} days"
 *     inbound.tools          "{{count}} published tools"
 *     editor.notEditable     "{{count}} more files, …"
 *     profile.deleteAllBody  "…delete all {{count}} conversations…"
 *
 * Each reads wrong at one, and the last is a confirmation dialog
 * for deleting everything, which is a poor place to look sloppy.
 * They were split into `_one`/`_other`; i18next resolves the
 * suffix from the `count` the caller already passes, so no call
 * site changed.
 *
 * The other three interpolate a number that is not a count of
 * anything — a rate, a position in a sequence, an index — and
 * pluralising them would be wrong. They are named below, because
 * an exemption nobody wrote down is indistinguishable from a
 * miss.
 */

const CATALOGUE = JSON.parse(
  readFileSync(join(__dirname, '..', 'locales', 'en.json'), 'utf8'),
) as Record<string, unknown>;

/** `{{count}}` here is not a count of things. */
const NOT_A_COUNT: Record<string, string> = {
  'analytics.peak': 'a rate — "peak 40/day" has no singular form',
  'errors.retryAttempt': 'an ordinal inside a fraction — "attempt 1/3"',
  'counts.forkedAt': 'a position in the thread — "from message 4"',
};

function flatten(node: unknown, prefix = ''): Record<string, string> {
  const out: Record<string, string> = {};
  if (typeof node !== 'object' || node === null) return out;
  for (const [key, value] of Object.entries(node)) {
    if (typeof value === 'string') out[prefix + key] = value;
    else Object.assign(out, flatten(value, `${prefix}${key}.`));
  }
  return out;
}

const FLAT = flatten(CATALOGUE);
const INTERPOLATES_COUNT = Object.keys(FLAT).filter((key) =>
  FLAT[key].includes('{{count}}'),
);

describe('a counted thing has a singular', () => {
  it('there are counted strings to check', () => {
    // Otherwise the loop below passes by iterating nothing.
    expect(INTERPOLATES_COUNT.length).toBeGreaterThan(50);
  });

  it('every key interpolating a count is pluralised', () => {
    const bare = INTERPOLATES_COUNT.filter(
      (key) =>
        !key.endsWith('_one') && !key.endsWith('_other') && !(key in NOT_A_COUNT),
    );
    expect(bare).toEqual([]);
  });

  it('each plural key has its partner', () => {
    // `_other` alone renders nothing at one; `_one` alone
    // renders nothing at two. Half a plural is worse than none,
    // because it works in the case the author tested.
    for (const key of INTERPOLATES_COUNT) {
      if (key.endsWith('_one')) {
        expect(FLAT).toHaveProperty(key.replace(/_one$/, '_other'));
      }
      if (key.endsWith('_other')) {
        expect(FLAT).toHaveProperty(key.replace(/_other$/, '_one'));
      }
    }
  });

  it('the exemptions name keys that still exist', () => {
    // An exemption for a renamed key excuses nothing and quietly
    // covers whatever takes the name next.
    for (const key of Object.keys(NOT_A_COUNT)) {
      expect(FLAT, `${key} is exempted and no longer exists`).toHaveProperty(key);
    }
  });

  it('every exemption gives a reason', () => {
    for (const [key, why] of Object.entries(NOT_A_COUNT)) {
      expect(why.length, `${key} has no real reason`).toBeGreaterThan(20);
    }
  });
});
