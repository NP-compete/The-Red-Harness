import { describe, expect, it } from 'vitest';

import { presentRunDetails } from '@/lib/run-details';

const run = {
  id: 'run_8f3ac21',
  state: 'awaiting-approval' as const,
  model: 'large',
  startedAt: '14:02',
  tokens: 12400,
  tokenLimit: 50000,
  actions: 7,
  actionLimit: 40,
  durable: true,
};

describe('presentRunDetails', () => {
  it('shortens the reference so it fits a panel', () => {
    expect(presentRunDetails(run).reference).toBe('run_8f3a…');
  });

  it('describes the state in words', () => {
    expect(presentRunDetails(run).state).toBe('Waiting for your approval');
  });

  it('says a durable run survives a restart', () => {
    expect(presentRunDetails(run).note).toContain('survive');
  });

  it('says nothing special about an ordinary run', () => {
    expect(presentRunDetails({ ...run, durable: false }).note).toBe('');
  });

  it('shows spend against the allowance', () => {
    expect(presentRunDetails(run).tokens).toBe('12,400 of 50,000');
  });

  it('shows actions against their allowance', () => {
    expect(presentRunDetails(run).actions).toBe('7 of 40');
  });

  it('shows spend without an allowance when none is set', () => {
    const shown = presentRunDetails({ ...run, tokenLimit: null });
    expect(shown.tokens).toBe('12,400');
  });

  it('offers to stop a running run', () => {
    expect(presentRunDetails({ ...run, state: 'running' }).actionsAvailable).toEqual(['stop']);
  });

  it('offers nothing to stop once it has finished', () => {
    expect(presentRunDetails({ ...run, state: 'finished' }).actionsAvailable).toEqual([]);
  });

  it('offers approve and refuse while it waits', () => {
    expect(presentRunDetails(run).actionsAvailable).toEqual(['approve', 'refuse']);
  });

  it('warns when the allowance is nearly gone', () => {
    const shown = presentRunDetails({ ...run, tokens: 46000 });
    expect(shown.warning).toContain('allowance');
  });

  it('does not warn with plenty left', () => {
    expect(presentRunDetails(run).warning).toBeUndefined();
  });
});
