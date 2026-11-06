import { describe, expect, it } from 'vitest';

import { applyFilter } from '@/lib/run-filter';

const now = new Date('2026-10-27T09:00:00Z');

const runs = [
  {
    id: 'r1',
    agent: 'triage',
    outcome: 'ok' as const,
    at: '2026-10-27T08:00:00Z',
    title: 'Sort inbox',
    cost: 0.1,
  },
  {
    id: 'r2',
    agent: 'reporter',
    outcome: 'failed' as const,
    at: '2026-10-21T08:00:00Z',
    title: 'Weekly summary',
    cost: 2.5,
  },
  {
    id: 'r3',
    agent: 'triage',
    outcome: 'ok' as const,
    at: '2026-09-01T08:00:00Z',
    title: 'Sort inbox again',
    cost: 0.2,
  },
];

const noFilter = { agents: [], outcomes: [], since: null, text: '', minCost: null };

describe('applyFilter', () => {
  it('returns everything when nothing is filtered', () => {
    expect(applyFilter(runs, noFilter, now).matches).toHaveLength(3);
  });

  it('filters by agent', () => {
    const shown = applyFilter(runs, { ...noFilter, agents: ['triage'] }, now);
    expect(shown.matches.map((run) => run.id)).toEqual(['r1', 'r3']);
  });

  it('treats several agents as any of them', () => {
    const shown = applyFilter(runs, { ...noFilter, agents: ['triage', 'reporter'] }, now);
    expect(shown.matches).toHaveLength(3);
  });

  it('filters by outcome', () => {
    const shown = applyFilter(runs, { ...noFilter, outcomes: ['failed'] }, now);
    expect(shown.matches.map((run) => run.id)).toEqual(['r2']);
  });

  it('combines filters as all of them', () => {
    const shown = applyFilter(runs, { ...noFilter, agents: ['triage'], outcomes: ['failed'] }, now);
    expect(shown.matches).toEqual([]);
  });

  it('filters by how recent a run is', () => {
    const shown = applyFilter(runs, { ...noFilter, since: '7d' }, now);
    expect(shown.matches.map((run) => run.id)).toEqual(['r1', 'r2']);
  });

  it('filters by text in the title', () => {
    const shown = applyFilter(runs, { ...noFilter, text: 'inbox' }, now);
    expect(shown.matches.map((run) => run.id)).toEqual(['r1', 'r3']);
  });

  it('ignores case when matching text', () => {
    expect(applyFilter(runs, { ...noFilter, text: 'INBOX' }, now).matches).toHaveLength(2);
  });

  it('filters by cost', () => {
    const shown = applyFilter(runs, { ...noFilter, minCost: 1 }, now);
    expect(shown.matches.map((run) => run.id)).toEqual(['r2']);
  });

  it('says how many were hidden', () => {
    expect(applyFilter(runs, { ...noFilter, agents: ['triage'] }, now).hidden).toBe(1);
  });

  it('describes the filter in plain words', () => {
    const shown = applyFilter(runs, { ...noFilter, agents: ['triage'], since: '7d' }, now);
    expect(shown.description).toBe('triage, last 7 days');
  });

  it('says plainly when nothing is filtered', () => {
    expect(applyFilter(runs, noFilter, now).description).toBe('everything');
  });

  it('says plainly when a filter matches nothing', () => {
    const shown = applyFilter(runs, { ...noFilter, text: 'nothing like this' }, now);
    expect(shown.emptyMessage).toBe('No runs match this filter');
  });

  it('has no empty message when something matched', () => {
    expect(applyFilter(runs, noFilter, now).emptyMessage).toBe('');
  });

  it('refuses a window it does not understand', () => {
    expect(() => applyFilter(runs, { ...noFilter, since: 'last tuesday' }, now)).toThrow();
  });
});
