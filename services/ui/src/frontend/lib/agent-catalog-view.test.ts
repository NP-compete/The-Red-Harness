import { describe, expect, it } from 'vitest';

import { presentCatalog } from '@/lib/agent-catalog-view';

const agents = [
  {
    name: 'triage',
    summary: 'Sorts incoming issues',
    licensed: true,
    hasSeat: true,
    missingScopes: [] as string[],
    deprecated: false,
    lastUsedAt: '2026-10-26T09:00:00Z',
  },
  {
    name: 'reporter',
    summary: 'Writes weekly summaries',
    licensed: true,
    hasSeat: false,
    missingScopes: [],
    deprecated: false,
    lastUsedAt: null as string | null,
  },
  {
    name: 'auditor',
    summary: 'Checks spending',
    licensed: false,
    hasSeat: false,
    missingScopes: ['finance.read'],
    deprecated: false,
    lastUsedAt: null as string | null,
  },
];

const now = new Date('2026-10-27T09:00:00Z');
const card = (name: string) =>
  presentCatalog(agents, now).cards.find((candidate) => candidate.name === name)!;

describe('presentCatalog', () => {
  it('shows an agent the person can use as usable', () => {
    expect(card('triage').usable).toBe(true);
  });

  it('shows an agent needing a seat as not usable', () => {
    expect(card('reporter').usable).toBe(false);
  });

  it('says what is missing when there is no seat', () => {
    expect(card('reporter').blockedBy).toBe('You need a seat on this team');
  });

  it('says what is missing when the team has no licence', () => {
    expect(card('auditor').blockedBy).toBe('Your organisation is not licensed for this');
  });

  it('mentions a licence before a missing permission', () => {
    expect(card('auditor').blockedBy).not.toContain('finance.read');
  });

  it('says plainly when only a permission is missing', () => {
    const scoped = [{ ...agents[0], missingScopes: ['finance.read'] }];
    expect(presentCatalog(scoped, now).cards[0].blockedBy).toBe('You need access to finance.read');
  });

  it('has nothing blocking a usable agent', () => {
    expect(card('triage').blockedBy).toBe('');
  });

  it('offers to start a usable agent', () => {
    expect(card('triage').action).toBe('start');
  });

  it('offers to ask for access to an unusable one', () => {
    expect(card('reporter').action).toBe('request-access');
  });

  it('puts usable agents first', () => {
    expect(presentCatalog(agents, now).cards[0].name).toBe('triage');
  });

  it('says when an agent was last used', () => {
    expect(card('triage').lastUsed).toBe('yesterday');
  });

  it('says plainly when an agent has never been used', () => {
    expect(card('reporter').lastUsed).toBe('never used');
  });

  it('marks a deprecated agent without hiding it', () => {
    const old = [{ ...agents[0], deprecated: true }];
    expect(presentCatalog(old, now).cards[0].note).toBe('Being retired');
  });

  it('counts how many the person can actually use', () => {
    expect(presentCatalog(agents, now).usableCount).toBe(1);
  });

  it('says plainly when none are available', () => {
    expect(presentCatalog([], now).emptyMessage).toBe('No agents are available to you yet');
  });
});
