import { describe, expect, it } from 'vitest';

import published from '@/contract/decisions.json';
import { CODES, OUTCOMES } from '@/lib/contract';

describe('decision contract', () => {
  it('knows every refusal code the agent can send', () => {
    expect([...CODES].sort()).toEqual([...published.refusal_codes].sort());
  });

  it('claims no code the agent cannot send', () => {
    expect(CODES.every((code) => published.refusal_codes.includes(code))).toBe(true);
  });

  it('knows every outcome the agent can send', () => {
    expect([...OUTCOMES].sort()).toEqual([...published.outcomes].sort());
  });

  it('has a remedy for every code it knows', () => {
    expect(CODES.every((code) => Boolean(published.remedies[code]))).toBe(true);
  });
});
