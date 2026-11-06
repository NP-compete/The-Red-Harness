import { describe, expect, it } from 'vitest';

import { presentIncident } from '@/lib/incident-banner';

const now = new Date('2026-10-27T09:00:00Z');

const posture = {
  reads: true,
  interactiveRuns: true,
  unattendedRuns: false,
  approveEverythingRisky: true,
  concurrencyFactor: 0.5,
  declaredBy: 'on-call',
  reason: 'elevated failures in the mail tool',
  until: '2026-10-27T11:00:00Z',
};

describe('presentIncident', () => {
  it('shows nothing when everything is normal', () => {
    const normal = {
      ...posture,
      unattendedRuns: true,
      approveEverythingRisky: false,
      concurrencyFactor: 1,
      declaredBy: '',
      reason: '',
      until: null,
    };
    expect(presentIncident(normal, now)).toBeNull();
  });

  it('says what is wrong in the words it was given', () => {
    expect(presentIncident(posture, now)?.headline).toBe('elevated failures in the mail tool');
  });

  it('lists what has been turned off', () => {
    expect(presentIncident(posture, now)?.restrictions).toEqual([
      'Scheduled runs are paused',
      'Risky steps need approval',
      'Fewer runs at a time',
    ]);
  });

  it('says plainly when nobody can start a run', () => {
    const severe = { ...posture, interactiveRuns: false, concurrencyFactor: 0.25 };
    expect(presentIncident(severe, now)?.restrictions[0]).toBe('New runs are paused');
  });

  it('reassures that reading still works', () => {
    const severe = { ...posture, interactiveRuns: false };
    expect(presentIncident(severe, now)?.note).toBe('You can still read existing conversations');
  });

  it('says when it is expected to lift', () => {
    expect(presentIncident(posture, now)?.until).toBe('expected to lift in 2 hours');
  });

  it('says who declared it', () => {
    expect(presentIncident(posture, now)?.declaredBy).toBe('on-call');
  });

  it('treats a partial restriction as a warning', () => {
    expect(presentIncident(posture, now)?.severity).toBe('medium');
  });

  it('treats a full stop as serious', () => {
    const severe = { ...posture, interactiveRuns: false };
    expect(presentIncident(severe, now)?.severity).toBe('high');
  });

  it('cannot be dismissed while it applies', () => {
    expect(presentIncident(posture, now)?.dismissible).toBe(false);
  });

  it('says plainly when the end time has passed', () => {
    const over = { ...posture, until: '2026-10-27T08:00:00Z' };
    expect(presentIncident(over, now)?.until).toBe('overdue to lift');
  });

  it('does not promise a lift time it was not given', () => {
    const openEnded = { ...posture, until: null };
    expect(presentIncident(openEnded, now)?.until).toBe('');
  });
});
