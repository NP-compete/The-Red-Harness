import { describe, expect, it } from 'vitest';

import { presentCapacity } from '@/lib/capacity';

const tier = {
  name: 'API requests',
  target: '1,000 / second',
  measured: '1,040 / second',
  goodput: 99.2,
};

describe('presentCapacity', () => {
  it('shows what was asked for and what was measured', () => {
    const row = presentCapacity([tier]).rows[0];
    expect(row.target).toBe('1,000 / second');
    expect(row.measured).toBe('1,040 / second');
  });

  it('calls a tier healthy when it meets its goodput threshold', () => {
    expect(presentCapacity([tier]).rows[0].status).toBe('ok');
  });

  it('warns when goodput slips below the threshold', () => {
    expect(presentCapacity([{ ...tier, goodput: 96 }]).rows[0].status).toBe('warn');
  });

  it('fails a tier that is badly short', () => {
    expect(presentCapacity([{ ...tier, goodput: 80 }]).rows[0].status).toBe('fail');
  });

  it('says plainly when a tier was never measured', () => {
    const row = presentCapacity([{ name: 'Sandboxes', target: 'pool 24' }]).rows[0];
    expect(row.measured).toBe('not measured');
    expect(row.status).toBe('unknown');
  });

  it('marks a tier whose ceiling is somebody else quota', () => {
    const row = presentCapacity([{ ...tier, providerBound: true }]).rows[0];
    expect(row.note).toContain('quota');
  });

  it('keeps the order it was given, because the tiers build on each other', () => {
    const rows = presentCapacity([
      { name: 'first', target: 'a' },
      { name: 'second', target: 'b' },
    ]).rows;
    expect(rows.map((row) => row.name)).toEqual(['first', 'second']);
  });

  it('reports the worst tier as the overall state', () => {
    const shown = presentCapacity([tier, { ...tier, name: 'Streams', goodput: 80 }]);
    expect(shown.overall).toBe('fail');
  });

  it('is unknown overall when nothing has been measured', () => {
    expect(presentCapacity([{ name: 'Sandboxes', target: 'pool 24' }]).overall).toBe('unknown');
  });

  it('shows no rows without falling over', () => {
    const shown = presentCapacity([]);
    expect(shown.rows).toEqual([]);
    expect(shown.overall).toBe('unknown');
  });
});
