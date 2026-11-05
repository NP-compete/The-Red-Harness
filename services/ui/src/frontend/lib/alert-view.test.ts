import { describe, expect, it } from 'vitest';

import { presentAlerts } from '@/lib/alert-view';

const now = new Date('2026-10-27T09:00:00Z');

const alerts = [
  {
    id: 'a1',
    kind: 'break-glass-used',
    person: 'ana',
    severity: 4,
    count: 1,
    at: '2026-10-27T08:58:00Z',
    summary: 'ana: 1 × break-glass-used in the last hour',
    acknowledged: false,
  },
  {
    id: 'a2',
    kind: 'refusal',
    person: 'bo',
    severity: 1,
    count: 5,
    at: '2026-10-27T08:30:00Z',
    summary: 'bo: 5 × refusal in the last hour',
    acknowledged: false,
  },
];

describe('presentAlerts', () => {
  it('puts the most serious first', () => {
    expect(presentAlerts(alerts, now).rows[0].id).toBe('a1');
  });

  it('turns a severity number into a word', () => {
    expect(presentAlerts(alerts, now).rows[0].level).toBe('critical');
    expect(presentAlerts(alerts, now).rows[1].level).toBe('low');
  });

  it('says what happened in the words it was given', () => {
    expect(presentAlerts(alerts, now).rows[0].summary).toBe(alerts[0].summary);
  });

  it('says how long ago it happened', () => {
    expect(presentAlerts(alerts, now).rows[0].when).toBe('2 minutes ago');
  });

  it('counts the ones nobody has looked at', () => {
    expect(presentAlerts(alerts, now).unacknowledged).toBe(2);
  });

  it('does not count acknowledged alerts as outstanding', () => {
    const seen = alerts.map((alert) => ({ ...alert, acknowledged: true }));
    expect(presentAlerts(seen, now).unacknowledged).toBe(0);
  });

  it('keeps acknowledged alerts visible rather than hiding them', () => {
    const seen = alerts.map((alert) => ({ ...alert, acknowledged: true }));
    expect(presentAlerts(seen, now).rows).toHaveLength(2);
  });

  it('sinks acknowledged alerts below outstanding ones', () => {
    const mixed = [{ ...alerts[0], acknowledged: true }, alerts[1]];
    expect(presentAlerts(mixed, now).rows.map((row) => row.id)).toEqual(['a2', 'a1']);
  });

  it('offers to acknowledge an outstanding alert', () => {
    expect(presentAlerts(alerts, now).rows[0].action).toBe('acknowledge');
  });

  it('offers nothing on an alert already acknowledged', () => {
    const seen = [{ ...alerts[0], acknowledged: true }];
    expect(presentAlerts(seen, now).rows[0].action).toBe('none');
  });

  it('says plainly when nothing has fired', () => {
    expect(presentAlerts([], now).emptyMessage).toBe('Nothing has fired');
  });

  it('has no empty message when something has', () => {
    expect(presentAlerts(alerts, now).emptyMessage).toBe('');
  });

  it('flags when something critical is outstanding', () => {
    expect(presentAlerts(alerts, now).needsAttention).toBe(true);
  });

  it('does not flag when the critical one has been seen', () => {
    const mixed = [{ ...alerts[0], acknowledged: true }, alerts[1]];
    expect(presentAlerts(mixed, now).needsAttention).toBe(false);
  });
});
