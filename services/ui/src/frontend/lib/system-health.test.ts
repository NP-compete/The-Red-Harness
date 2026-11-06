import { describe, expect, it } from 'vitest';

import { presentSystemHealth } from '@/lib/system-health';

const systems = [
  { name: 'tracker', state: 'connected' as const },
  { name: 'docs', state: 'connected' as const },
  { name: 'mail', state: 'not-connected' as const },
  { name: 'warehouse', state: 'degraded' as const, retryInSeconds: 45 },
];

describe('presentSystemHealth', () => {
  it('describes each system in words', () => {
    const rows = presentSystemHealth(systems).rows;
    expect(rows.find((r) => r.name === 'tracker')?.status).toBe('Connected');
    expect(rows.find((r) => r.name === 'mail')?.status).toBe('Not connected');
  });

  it('says when a failing system will be tried again', () => {
    const row = presentSystemHealth(systems).rows.find((r) => r.name === 'warehouse');
    expect(row?.status).toBe('Unavailable, retrying in 45s');
  });

  it('offers to connect something that is not connected', () => {
    const row = presentSystemHealth(systems).rows.find((r) => r.name === 'mail');
    expect(row?.action).toBe('connect');
  });

  it('offers to retry something that is failing', () => {
    const row = presentSystemHealth(systems).rows.find((r) => r.name === 'warehouse');
    expect(row?.action).toBe('retry');
  });

  it('offers to disconnect something that works', () => {
    const row = presentSystemHealth(systems).rows.find((r) => r.name === 'tracker');
    expect(row?.action).toBe('disconnect');
  });

  it('puts what needs attention at the top', () => {
    const rows = presentSystemHealth(systems).rows;
    expect(rows.slice(0, 2).map((r) => r.name).sort()).toEqual(['mail', 'warehouse']);
  });

  it('summarises the state of everything', () => {
    expect(presentSystemHealth(systems).summary).toBe('2 connected, 1 needs attention, 1 failing');
  });

  it('says all is well when it is', () => {
    const healthy = systems.slice(0, 2);
    expect(presentSystemHealth(healthy).summary).toBe('2 connected');
  });

  it('handles an agent with nothing connected', () => {
    const shown = presentSystemHealth([]);
    expect(shown.rows).toEqual([]);
    expect(shown.summary).toBe('Nothing connected yet');
  });

  it('does not invent a retry time when there is none', () => {
    const shown = presentSystemHealth([{ name: 'x', state: 'degraded' }]);
    expect(shown.rows[0].status).toBe('Unavailable');
  });
});
