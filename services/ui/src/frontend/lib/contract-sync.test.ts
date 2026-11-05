import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

// The copy this app reads is only useful if it still matches the one
// the agent publishes.
const MINE = resolve(__dirname, '../contract/decisions.json');
const THEIRS = resolve(__dirname, '../../../../template-agent/contract/decisions.json');

describe('the published decision contract', () => {
  it('is present in this app', () => {
    expect(existsSync(MINE)).toBe(true);
  });

  it.runIf(existsSync(THEIRS))('matches the published copy', () => {
    expect(JSON.parse(readFileSync(MINE, 'utf8'))).toEqual(
      JSON.parse(readFileSync(THEIRS, 'utf8')),
    );
  });
});
