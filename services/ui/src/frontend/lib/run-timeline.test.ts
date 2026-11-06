import { describe, expect, it } from 'vitest';

import { presentTimeline } from '@/lib/run-timeline';

const events = [
  { at: '2026-10-27T09:00:00Z', kind: 'started' as const, label: 'Run started' },
  { at: '2026-10-27T09:00:02Z', kind: 'tool' as const, label: 'search' },
  { at: '2026-10-27T09:00:05Z', kind: 'tool' as const, label: 'fetch' },
  { at: '2026-10-27T09:05:05Z', kind: 'finished' as const, label: 'Run finished' },
];

describe('presentTimeline', () => {
  it('keeps the events in the order they happened', () => {
    expect(presentTimeline(events).steps.map((step) => step.label)).toEqual([
      'Run started',
      'search',
      'fetch',
      'Run finished',
    ]);
  });

  it('orders events that arrive out of order', () => {
    const shuffled = [events[2], events[0], events[3], events[1]];
    expect(presentTimeline(shuffled).steps.map((step) => step.label)).toEqual([
      'Run started',
      'search',
      'fetch',
      'Run finished',
    ]);
  });

  it('says how long each step took', () => {
    expect(presentTimeline(events).steps[1].took).toBe('3s');
  });

  it('gives the last step no duration rather than guessing one', () => {
    expect(presentTimeline(events).steps.at(-1)?.took).toBe('');
  });

  it('gives the total time for the run', () => {
    expect(presentTimeline(events).total).toBe('5m 5s');
  });

  it('marks the step that took most of the time', () => {
    expect(presentTimeline(events).steps[2].slowest).toBe(true);
  });

  it('marks only one step as the slowest', () => {
    expect(presentTimeline(events).steps.filter((step) => step.slowest)).toHaveLength(1);
  });

  it('does not mark a slowest step when nothing stands out', () => {
    const even = [
      { at: '2026-10-27T09:00:00Z', kind: 'started' as const, label: 'a' },
      { at: '2026-10-27T09:00:01Z', kind: 'tool' as const, label: 'b' },
      { at: '2026-10-27T09:00:02Z', kind: 'tool' as const, label: 'c' },
    ];
    expect(presentTimeline(even).steps.some((step) => step.slowest)).toBe(false);
  });

  it('shows a gap where the run was waiting on a person', () => {
    const waited = [
      { at: '2026-10-27T09:00:00Z', kind: 'started' as const, label: 'Run started' },
      { at: '2026-10-27T09:00:01Z', kind: 'awaiting-approval' as const, label: 'Waiting for Bo' },
      { at: '2026-10-27T09:40:01Z', kind: 'tool' as const, label: 'deploy' },
    ];
    expect(presentTimeline(waited).steps[1].waiting).toBe(true);
  });

  it('separates time waiting on a person from time spent working', () => {
    const waited = [
      { at: '2026-10-27T09:00:00Z', kind: 'started' as const, label: 'Run started' },
      { at: '2026-10-27T09:00:01Z', kind: 'awaiting-approval' as const, label: 'Waiting for Bo' },
      { at: '2026-10-27T09:40:01Z', kind: 'tool' as const, label: 'deploy' },
    ];
    expect(presentTimeline(waited).waitingTotal).toBe('40m 0s');
  });

  it('reports no waiting when nobody was waited on', () => {
    expect(presentTimeline(events).waitingTotal).toBe('');
  });

  it('says a run is still going when it has not finished', () => {
    expect(presentTimeline(events.slice(0, 3)).finished).toBe(false);
  });

  it('says a run is finished when it has', () => {
    expect(presentTimeline(events).finished).toBe(true);
  });

  it('handles an empty run without inventing a timeline', () => {
    const shown = presentTimeline([]);
    expect(shown.steps).toEqual([]);
    expect(shown.total).toBe('');
  });
});
