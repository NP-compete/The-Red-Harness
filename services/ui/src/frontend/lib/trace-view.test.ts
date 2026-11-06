import { describe, expect, it } from 'vitest';

import { presentTrace } from '@/lib/trace-view';

const trace = {
  roots: [
    {
      spanId: 'run',
      name: 'run',
      durationMs: 1000,
      ownMs: 200,
      attributes: { agent: 'triage' },
      children: [
        {
          spanId: 'search',
          name: 'search',
          durationMs: 300,
          ownMs: 300,
          attributes: {},
          children: [],
        },
        {
          spanId: 'write',
          name: 'write',
          durationMs: 500,
          ownMs: 500,
          attributes: {},
          children: [],
        },
      ],
    },
  ],
  orphans: [] as string[],
  totalMs: 1000,
  slowest: 'write',
};

describe('presentTrace', () => {
  it('flattens the tree for display', () => {
    expect(presentTrace(trace).rows.map((row) => row.spanId)).toEqual(['run', 'search', 'write']);
  });

  it('shows how deep each row sits', () => {
    expect(presentTrace(trace).rows.map((row) => row.depth)).toEqual([0, 1, 1]);
  });

  it('shows each duration readably', () => {
    expect(presentTrace(trace).rows[0].duration).toBe('1.0s');
  });

  it('shows a short duration in milliseconds', () => {
    expect(presentTrace(trace).rows[1].duration).toBe('300ms');
  });

  it('shows each row’s share of the whole', () => {
    expect(presentTrace(trace).rows[2].share).toBeCloseTo(0.5, 2);
  });

  it('marks the slowest step', () => {
    const rows = presentTrace(trace).rows;
    expect(rows.find((row) => row.spanId === 'write')?.slowest).toBe(true);
  });

  it('does not mark the others as slowest', () => {
    expect(presentTrace(trace).rows[0].slowest).toBe(false);
  });

  it('shows time spent in the step itself', () => {
    expect(presentTrace(trace).rows[0].own).toBe('200ms');
  });

  it('gives the total', () => {
    expect(presentTrace(trace).total).toBe('1.0s');
  });

  it('says plainly when parents were lost', () => {
    const broken = { ...trace, orphans: ['stray'] };
    expect(presentTrace(broken).warning).toBe('1 step lost its parent and is shown at the top');
  });

  it('has no warning for a whole trace', () => {
    expect(presentTrace(trace).warning).toBe('');
  });

  it('shows attributes that were kept', () => {
    expect(presentTrace(trace).rows[0].attributes).toEqual([{ key: 'agent', value: 'triage' }]);
  });

  it('shows no attributes when there are none', () => {
    expect(presentTrace(trace).rows[1].attributes).toEqual([]);
  });

  it('handles a trace with nothing in it', () => {
    const empty = { roots: [], orphans: [], totalMs: 0, slowest: '' };
    expect(presentTrace(empty).rows).toEqual([]);
  });
});
