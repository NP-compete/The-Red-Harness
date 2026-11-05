import { describe, expect, it } from 'vitest';

import { shouldAsk } from '@/lib/ask-permission';

/**
 * When to ask for notification permission.
 *
 * Never on first load. A prompt before somebody has seen what the
 * product does is a prompt they refuse, and a refusal is permanent
 * in most browsers — one badly-timed ask costs the feature for good.
 */
const supported = {
  supported: true,
  permission: 'default' as NotificationPermission,
  startedARun: true,
  alreadyAsked: false,
};

describe('shouldAsk', () => {
  it('asks once somebody has started a run', () => {
    expect(shouldAsk(supported)).toBe(true);
  });

  it('does not ask before they have done anything', () => {
    expect(shouldAsk({ ...supported, startedARun: false })).toBe(false);
  });

  it('does not ask on a platform where delivery is unreliable', () => {
    expect(shouldAsk({ ...supported, supported: false })).toBe(false);
  });

  it('does not ask again once permission is granted', () => {
    expect(shouldAsk({ ...supported, permission: 'granted' })).toBe(false);
  });

  it('does not ask again after a refusal', () => {
    // The browser would not show it anyway, and asking is how an
    // app earns a permanent block.
    expect(shouldAsk({ ...supported, permission: 'denied' })).toBe(false);
  });

  it('does not ask twice in one session', () => {
    expect(shouldAsk({ ...supported, alreadyAsked: true })).toBe(false);
  });
});
