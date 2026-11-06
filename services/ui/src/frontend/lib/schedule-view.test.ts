import { describe, expect, it } from 'vitest';

import { presentSchedule } from '@/lib/schedule-view';

const now = new Date('2026-10-27T09:00:00Z');

const schedule = {
  name: 'Nightly digest',
  everySeconds: 86_400,
  nextAt: '2026-10-28T07:00:00Z',
  paused: false,
  missed: 0,
  lastOutcome: 'ok' as const,
};

describe('presentSchedule', () => {
  it('says how often it runs in plain words', () => {
    expect(presentSchedule(schedule, now).cadence).toBe('every day');
  });

  it('describes an hourly schedule', () => {
    expect(presentSchedule({ ...schedule, everySeconds: 3600 }, now).cadence).toBe('every hour');
  });

  it('describes an unusual interval in hours', () => {
    expect(presentSchedule({ ...schedule, everySeconds: 7200 }, now).cadence).toBe('every 2 hours');
  });

  it('says when it will next run', () => {
    expect(presentSchedule(schedule, now).next).toBe('in 22 hours');
  });

  it('says a paused schedule is not running', () => {
    const shown = presentSchedule({ ...schedule, paused: true }, now);
    expect(shown.next).toBe('paused');
  });

  it('still says when it would resume', () => {
    const shown = presentSchedule({ ...schedule, paused: true }, now);
    expect(shown.wouldResume).toBe('in 22 hours');
  });

  it('reports missed runs without alarming language when there are none', () => {
    expect(presentSchedule(schedule, now).note).toBe('');
  });

  it('says plainly when runs were missed', () => {
    expect(presentSchedule({ ...schedule, missed: 71 }, now).note).toContain('71 runs were missed');
  });

  it('reassures that only one catch-up will happen', () => {
    expect(presentSchedule({ ...schedule, missed: 71 }, now).note).toContain('once');
  });

  it('flags a schedule whose last run failed', () => {
    expect(presentSchedule({ ...schedule, lastOutcome: 'failed' }, now).needsAttention).toBe(true);
  });

  it('does not flag a healthy schedule', () => {
    expect(presentSchedule(schedule, now).needsAttention).toBe(false);
  });

  it('offers to pause a running schedule and resume a paused one', () => {
    expect(presentSchedule(schedule, now).action).toBe('pause');
    expect(presentSchedule({ ...schedule, paused: true }, now).action).toBe('resume');
  });
});
