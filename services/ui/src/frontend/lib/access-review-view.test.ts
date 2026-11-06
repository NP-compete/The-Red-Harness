import { describe, expect, it } from 'vitest';

import { presentAccessReview } from '@/lib/access-review-view';

const rows = [
  { subject: 'old@example.com', agent: 'support', via: 'direct', lastUsedDays: null, flagged: true },
  { subject: 'me@example.com', agent: 'finance', via: 'group:sre', lastUsedDays: 200, flagged: true },
  { subject: 'me@example.com', agent: 'support', via: 'group:sre', lastUsedDays: 2, flagged: false },
];

describe('presentAccessReview', () => {
  it('describes how access was granted in words', () => {
    const shown = presentAccessReview(rows);
    expect(shown.rows[0].source).toBe('Granted directly');
    expect(shown.rows[1].source).toBe('Through the group sre');
  });

  it('says when access was last used', () => {
    expect(presentAccessReview(rows).rows[1].lastUsed).toBe('200 days ago');
  });

  it('says plainly when access has never been used', () => {
    expect(presentAccessReview(rows).rows[0].lastUsed).toBe('never used');
  });

  it('uses recent wording for recent use', () => {
    expect(presentAccessReview(rows).rows[2].lastUsed).toBe('2 days ago');
  });

  it('offers to revoke a flagged grant', () => {
    expect(presentAccessReview(rows).rows[0].action).toBe('revoke');
  });

  it('offers to keep an unflagged grant without suggesting removal', () => {
    expect(presentAccessReview(rows).rows[2].action).toBeUndefined();
  });

  it('counts what the reviewer has to decide about', () => {
    expect(presentAccessReview(rows).toDecide).toBe(2);
  });

  it('says when there is nothing to decide', () => {
    const clean = rows.filter((r) => !r.flagged);
    expect(presentAccessReview(clean).summary).toContain('Nothing needs');
  });

  it('summarises how much needs attention', () => {
    expect(presentAccessReview(rows).summary).toBe('2 of 3 grants need a decision');
  });

  it('handles an empty review', () => {
    const shown = presentAccessReview([]);
    expect(shown.rows).toEqual([]);
    expect(shown.summary).toContain('No access');
  });
});
