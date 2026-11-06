import { describe, expect, it } from 'vitest';

import { resolveCapability } from '@/lib/capability';

describe('resolveCapability', () => {
  it('is off when nothing enables it', () => {
    expect(resolveCapability({ name: 'browsing' }).enabled).toBe(false);
  });

  it('is on when the deployment enables it and nothing narrows it', () => {
    const shown = resolveCapability({ name: 'browsing', deployment: true });
    expect(shown.enabled).toBe(true);
    expect(shown.decidedBy).toBe('deployment');
  });

  it('lets an agent narrow what the deployment allows', () => {
    const shown = resolveCapability({ name: 'browsing', deployment: true, agent: false });
    expect(shown.enabled).toBe(false);
    expect(shown.decidedBy).toBe('agent');
  });

  it('does not let an agent widen what the deployment forbids', () => {
    const shown = resolveCapability({ name: 'browsing', deployment: false, agent: true });
    expect(shown.enabled).toBe(false);
    expect(shown.decidedBy).toBe('deployment');
  });

  it('does not let a person widen what their agent forbids', () => {
    const shown = resolveCapability({
      name: 'browsing',
      deployment: true,
      agent: false,
      user: true,
    });
    expect(shown.enabled).toBe(false);
    expect(shown.decidedBy).toBe('agent');
  });

  it('lets a person narrow it for themselves', () => {
    const shown = resolveCapability({
      name: 'browsing',
      deployment: true,
      agent: true,
      user: false,
    });
    expect(shown.enabled).toBe(false);
    expect(shown.decidedBy).toBe('user');
  });

  it('cannot be switched on while a requirement is missing', () => {
    const shown = resolveCapability({
      name: 'browsing',
      deployment: true,
      requires: [{ name: 'isolated runtime', met: false }],
    });
    expect(shown.enabled).toBe(false);
    expect(shown.togglable).toBe(false);
    expect(shown.blockedBy).toEqual(['isolated runtime']);
  });

  it('is togglable once every requirement is met', () => {
    const shown = resolveCapability({
      name: 'browsing',
      deployment: true,
      requires: [{ name: 'isolated runtime', met: true }],
    });
    expect(shown.togglable).toBe(true);
    expect(shown.blockedBy).toEqual([]);
  });

  it('reports every unmet requirement, not just the first', () => {
    const shown = resolveCapability({
      name: 'browsing',
      requires: [
        { name: 'isolated runtime', met: false },
        { name: 'capacity reserved', met: false },
      ],
    });
    expect(shown.blockedBy).toEqual(['isolated runtime', 'capacity reserved']);
  });

  it('states the cost so it is read before the switch is flipped', () => {
    const shown = resolveCapability({ name: 'browsing', cost: 'Reads live web pages.' });
    expect(shown.cost).toBe('Reads live web pages.');
  });
});
