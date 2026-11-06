import { describe, expect, it } from 'vitest';

import { presentAudit } from '@/lib/audit';

const allowed = {
  at: '14:12',
  subject: 'someone@example.com',
  tool: 'tracker.search',
  outcome: 'allowed' as const,
};

describe('presentAudit', () => {
  it('says what happened in words rather than codes', () => {
    expect(presentAudit([allowed]).rows[0].summary).toBe('Allowed tracker.search');
  });

  it('names who the action ran as', () => {
    expect(presentAudit([allowed]).rows[0].subject).toBe('someone@example.com');
  });

  it('explains a refusal by its cause', () => {
    const rows = presentAudit([
      { ...allowed, outcome: 'refused', code: 'no_authority' },
    ]).rows;
    expect(rows[0].summary).toBe('Refused tracker.search — not connected');
  });

  it('explains a budget refusal differently from a policy one', () => {
    const [budget, policy] = presentAudit([
      { ...allowed, outcome: 'refused', code: 'budget_exhausted' },
      { ...allowed, outcome: 'refused', code: 'policy_denied' },
    ]).rows;
    expect(budget.summary).toContain('out of budget');
    expect(policy.summary).toContain('not allowed');
  });

  it('marks a request that waited for a person', () => {
    const rows = presentAudit([{ ...allowed, outcome: 'needs_approval' }]).rows;
    expect(rows[0].summary).toBe('Asked before tracker.search');
  });

  it('flags entries from a conversation that read outside content', () => {
    const rows = presentAudit([{ ...allowed, trust: 'untrusted_read' }]).rows;
    expect(rows[0].flagged).toBe(true);
  });

  it('does not flag an ordinary entry', () => {
    expect(presentAudit([allowed]).rows[0].flagged).toBe(false);
  });

  it('keeps entries newest first', () => {
    const rows = presentAudit([
      { ...allowed, at: '09:00' },
      { ...allowed, at: '14:12' },
    ]).rows;
    expect(rows.map((row) => row.at)).toEqual(['14:12', '09:00']);
  });

  it('counts what it is showing', () => {
    const shown = presentAudit([allowed, { ...allowed, outcome: 'refused', code: 'policy_denied' }]);
    expect(shown.counts).toEqual({ allowed: 1, needs_approval: 0, refused: 1, unavailable: 0 });
  });

  it('shows an empty log without inventing rows', () => {
    const shown = presentAudit([]);
    expect(shown.rows).toEqual([]);
    expect(shown.empty).toBe(true);
  });
});
