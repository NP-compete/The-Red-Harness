import { describe, expect, it } from 'vitest';

import { presentTriggers } from '@/lib/trigger-view';

const trigger = {
  id: 'tr-1',
  source: 'issue-tracker',
  eventType: 'issue.opened',
  agent: 'Triage',
  paused: false,
  verified: true,
  lastDelivery: { at: '2026-10-27T08:00:00Z', outcome: 'ok' as const },
  deliveriesToday: 12,
};

const now = new Date('2026-10-27T09:00:00Z');

describe('presentTriggers', () => {
  it('names what starts the run and what it starts', () => {
    const [shown] = presentTriggers([trigger], now);
    expect(shown.summary).toBe('issue.opened from issue-tracker starts Triage');
  });

  it('warns when the source is not verified', () => {
    const [shown] = presentTriggers([{ ...trigger, verified: false }], now);
    expect(shown.warning).toContain('not verified');
  });

  it('has no warning for a verified source', () => {
    expect(presentTriggers([trigger], now)[0].warning).toBe('');
  });

  it('refuses to treat an unverified source as healthy', () => {
    expect(presentTriggers([{ ...trigger, verified: false }], now)[0].healthy).toBe(false);
  });

  it('says when the last delivery arrived', () => {
    expect(presentTriggers([trigger], now)[0].lastDelivery).toBe('1 hour ago');
  });

  it('says plainly when nothing has ever arrived', () => {
    const silent = { ...trigger, lastDelivery: null, deliveriesToday: 0 };
    expect(presentTriggers([silent], now)[0].lastDelivery).toBe('nothing yet');
  });

  it('flags a trigger that has never fired as needing a look', () => {
    const silent = { ...trigger, lastDelivery: null, deliveriesToday: 0 };
    expect(presentTriggers([silent], now)[0].healthy).toBe(false);
  });

  it('flags a trigger whose last delivery failed', () => {
    const broken = { ...trigger, lastDelivery: { at: trigger.lastDelivery.at, outcome: 'failed' as const } };
    expect(presentTriggers([broken], now)[0].healthy).toBe(false);
  });

  it('says a paused trigger is paused rather than broken', () => {
    const shown = presentTriggers([{ ...trigger, paused: true }], now)[0];
    expect(shown.state).toBe('paused');
    expect(shown.healthy).toBe(true);
  });

  it('counts the runs it caused today', () => {
    expect(presentTriggers([trigger], now)[0].volume).toBe('12 runs today');
  });

  it('puts the triggers that need attention first', () => {
    const shown = presentTriggers(
      [trigger, { ...trigger, id: 'tr-2', verified: false }],
      now,
    );
    expect(shown.map((t) => t.id)).toEqual(['tr-2', 'tr-1']);
  });

  it('shows nothing rather than inventing a trigger', () => {
    expect(presentTriggers([], now)).toEqual([]);
  });
});
