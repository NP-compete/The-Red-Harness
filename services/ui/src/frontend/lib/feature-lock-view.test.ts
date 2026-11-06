import { describe, expect, it } from 'vitest';

import { presentFeatureLock } from '@/lib/feature-lock-view';

const now = new Date('2026-10-27T09:00:00Z');

const allowed = {
  feature: 'unattended-runs',
  label: 'Scheduled runs',
  permitted: true,
  reason: null as string | null,
  selfServe: false,
  onTrial: false,
  trialEnds: null as string | null,
};

describe('presentFeatureLock', () => {
  it('shows nothing when a feature is simply available', () => {
    expect(presentFeatureLock(allowed, now)).toBeNull();
  });

  it('says plainly when a feature is off but available on this plan', () => {
    const off = { ...allowed, permitted: false, reason: 'turned-off', selfServe: true };
    expect(presentFeatureLock(off, now)?.headline).toBe('Scheduled runs is turned off');
  });

  it('says an administrator can turn it on', () => {
    const off = { ...allowed, permitted: false, reason: 'turned-off', selfServe: true };
    expect(presentFeatureLock(off, now)?.detail).toBe('An administrator can turn this on');
  });

  it('offers to turn it on when that is possible here', () => {
    const off = { ...allowed, permitted: false, reason: 'turned-off', selfServe: true };
    expect(presentFeatureLock(off, now)?.action).toBe('enable');
  });

  it('says plainly when a feature is not on this plan', () => {
    const locked = { ...allowed, permitted: false, reason: 'not-in-plan' };
    expect(presentFeatureLock(locked, now)?.headline).toBe('Scheduled runs is not on your plan');
  });

  it('offers to ask about upgrading rather than a switch', () => {
    const locked = { ...allowed, permitted: false, reason: 'not-in-plan' };
    expect(presentFeatureLock(locked, now)?.action).toBe('ask-about-plan');
  });

  it('says plainly when a trial has ended', () => {
    const over = { ...allowed, permitted: false, reason: 'trial-ended' };
    expect(presentFeatureLock(over, now)?.headline).toBe('Your trial of Scheduled runs has ended');
  });

  it('says plainly when everything is suspended', () => {
    const suspended = { ...allowed, permitted: false, reason: 'suspended' };
    expect(presentFeatureLock(suspended, now)?.headline).toBe('Your organisation’s access is suspended');
  });

  it('treats suspension as the most serious', () => {
    const suspended = { ...allowed, permitted: false, reason: 'suspended' };
    expect(presentFeatureLock(suspended, now)?.severity).toBe('high');
  });

  it('treats a plan limit as ordinary', () => {
    const locked = { ...allowed, permitted: false, reason: 'not-in-plan' };
    expect(presentFeatureLock(locked, now)?.severity).toBe('info');
  });

  it('shows a trial that is running, without blocking anything', () => {
    const trial = {
      ...allowed,
      onTrial: true,
      trialEnds: '2026-11-03T09:00:00Z',
    };
    expect(presentFeatureLock(trial, now)?.headline).toBe('Scheduled runs is on trial');
  });

  it('says how long a trial has left', () => {
    const trial = { ...allowed, onTrial: true, trialEnds: '2026-11-03T09:00:00Z' };
    expect(presentFeatureLock(trial, now)?.detail).toBe('7 days left');
  });

  it('does not lock a feature that is on trial', () => {
    const trial = { ...allowed, onTrial: true, trialEnds: '2026-11-03T09:00:00Z' };
    expect(presentFeatureLock(trial, now)?.locked).toBe(false);
  });

  it('locks a feature that is unavailable', () => {
    const locked = { ...allowed, permitted: false, reason: 'not-in-plan' };
    expect(presentFeatureLock(locked, now)?.locked).toBe(true);
  });
});
