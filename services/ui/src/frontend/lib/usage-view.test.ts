import { describe, expect, it } from 'vitest';

import { presentUsage } from '@/lib/usage-view';

const usage = {
  totals: { tokens: 1_234_567, approvals: 42, refusals: 7, runs: 310 },
  perTeam: { sre: { tokens: 800_000, runs: 200 }, platform: { tokens: 434_567, runs: 110 } },
  discloses: false,
  period: 'last 30 days',
};

describe('presentUsage', () => {
  it('says which period it covers', () => {
    expect(presentUsage(usage).period).toBe('last 30 days');
  });

  it('separates thousands so the numbers can be read', () => {
    const row = presentUsage(usage).headline.find((r) => r.label === 'Tokens');
    expect(row?.value).toBe('1,234,567');
  });

  it('leads with runs rather than tokens, because that is what people did', () => {
    expect(presentUsage(usage).headline[0].label).toBe('Runs');
  });

  it('shows how often the agent asked before acting', () => {
    const row = presentUsage(usage).headline.find((r) => r.label === 'Asked first');
    expect(row?.value).toBe('42');
  });

  it('shows refusals separately from approvals', () => {
    const row = presentUsage(usage).headline.find((r) => r.label === 'Refused');
    expect(row?.value).toBe('7');
  });

  it('orders teams by use', () => {
    expect(presentUsage(usage).teams.map((t) => t.name)).toEqual(['sre', 'platform']);
  });

  it('shows each team share of the whole', () => {
    expect(presentUsage(usage).teams[0].share).toBe('65%');
  });

  it('says plainly when the report names nobody', () => {
    expect(presentUsage(usage).disclosure).toContain('No individual');
  });

  it('warns when the report does name individuals', () => {
    expect(presentUsage({ ...usage, discloses: true }).disclosure).toContain('names individuals');
  });

  it('handles a period with no activity', () => {
    const quiet = { ...usage, totals: { tokens: 0, approvals: 0, refusals: 0, runs: 0 }, perTeam: {} };
    expect(presentUsage(quiet).teams).toEqual([]);
    expect(presentUsage(quiet).headline[0].value).toBe('0');
  });
});
