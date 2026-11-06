import { describe, expect, it } from 'vitest';

import { extensionCost } from './extension-cost';

const ran = (over: Record<string, number> = {}) => ({
  calls: 10,
  refusals: 0,
  refusal_rate: 0,
  average_ms: 12.3,
  slowest_ms: 40,
  ...over,
});

describe('extensionCost', () => {
  it('says nothing about one that has not run', () => {
    expect(extensionCost(null)).toBe('');
  });

  it('says how long it usually takes', () => {
    expect(extensionCost(ran())).toContain('12 ms');
  });

  it('says how many turns it has been on', () => {
    expect(extensionCost(ran({ calls: 10 }))).toContain('10 calls');
  });

  it('counts a single call as a call, not as calls', () => {
    expect(extensionCost(ran({ calls: 1 }))).toContain('1 call');
    expect(extensionCost(ran({ calls: 1 }))).not.toContain('1 calls');
  });

  it('says nothing about refusals when it has refused nothing', () => {
    expect(extensionCost(ran())).not.toMatch(/refus/i);
  });

  it('says how often it refuses when it does', () => {
    expect(extensionCost(ran({ refusals: 2, refusal_rate: 0.2 }))).toMatch(/20%/);
  });

  it('reports the slowest call when it is far off the usual', () => {
    // An extension that is usually fast and occasionally very slow
    // reads as fine on the average alone.
    expect(extensionCost(ran({ average_ms: 12, slowest_ms: 900 }))).toContain('900 ms');
  });

  it('does not repeat the figure when every call takes the same', () => {
    const said = extensionCost(ran({ average_ms: 12.3, slowest_ms: 12.4 }));
    expect(said.match(/12 ms/g)).toHaveLength(1);
  });

  it('rounds to something a person can read', () => {
    expect(extensionCost(ran({ average_ms: 12.345678 }))).not.toContain('12.345');
  });

  it('does not call a slow extension fast', () => {
    expect(extensionCost(ran({ average_ms: 2400, slowest_ms: 2500 }))).toContain(
      '2400 ms',
    );
  });
});
