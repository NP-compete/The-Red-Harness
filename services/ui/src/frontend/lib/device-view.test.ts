import { describe, expect, it } from 'vitest';

import { presentDevices } from '@/lib/device-view';

const now = new Date('2026-10-27T09:00:00Z');

const devices = [
  {
    fingerprint: 'abc123',
    label: 'work laptop',
    lastSeen: '2026-10-27T08:00:00Z',
    trusted: true,
    current: true,
  },
  {
    fingerprint: 'def456',
    label: 'home desktop',
    lastSeen: '2026-10-20T08:00:00Z',
    trusted: true,
    current: false,
  },
  {
    fingerprint: 'ghi789',
    label: 'old phone',
    lastSeen: '2026-01-01T08:00:00Z',
    trusted: true,
    current: false,
  },
];

describe('presentDevices', () => {
  it('puts the machine in use now first', () => {
    expect(presentDevices(devices, now).rows[0].fingerprint).toBe('abc123');
  });

  it('marks the machine in use now', () => {
    expect(presentDevices(devices, now).rows[0].isThisOne).toBe(true);
  });

  it('orders the rest by when they were last used', () => {
    expect(presentDevices(devices, now).rows.map((row) => row.display)).toEqual([
      'work laptop',
      'home desktop',
      'old phone',
    ]);
  });

  it('says when each was last used', () => {
    expect(presentDevices(devices, now).rows[1].lastUsed).toBe('7 days ago');
  });

  it('flags a machine nobody has used in a long time', () => {
    expect(presentDevices(devices, now).rows[2].stale).toBe(true);
  });

  it('does not flag a recently used machine', () => {
    expect(presentDevices(devices, now).rows[1].stale).toBe(false);
  });

  it('suggests removing a machine long unused', () => {
    expect(presentDevices(devices, now).rows[2].note).toBe('Not used in a long time — remove it?');
  });

  it('lets any other machine be signed out', () => {
    expect(presentDevices(devices, now).rows[1].action).toBe('sign-out');
  });

  it('does not offer to sign out the machine being used right now', () => {
    expect(presentDevices(devices, now).rows[0].action).toBe('none');
  });

  it('counts the machines', () => {
    expect(presentDevices(devices, now).count).toBe(3);
  });

  it('never shows the raw fingerprint to the person', () => {
    const shown = presentDevices(devices, now);
    expect(shown.rows.every((row) => row.display !== row.fingerprint)).toBe(true);
  });

  it('falls back to a readable name when a device has no label', () => {
    const unlabelled = [{ ...devices[0], label: '' }];
    expect(presentDevices(unlabelled, now).rows[0].display).toBe('Unnamed device');
  });

  it('says plainly when there is only this machine', () => {
    expect(presentDevices([devices[0]], now).emptyMessage).toBe(
      'This is the only machine signed in',
    );
  });

  it('has no such message when there are several', () => {
    expect(presentDevices(devices, now).emptyMessage).toBe('');
  });
});
