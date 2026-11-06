import { describe, expect, it } from 'vitest';

import { presentVersionPin } from '@/lib/version-pin-view';

const pinned = {
  version: '4.1',
  currentVersion: '4.2',
  outcome: 'pinned' as const,
  behaviourMayChange: false,
  reason: '',
  pinnedBy: 'system',
};

describe('presentVersionPin', () => {
  it('shows nothing when the thread is on the current version', () => {
    const current = { ...pinned, version: '4.2', outcome: 'current' as const };
    expect(presentVersionPin(current)).toBeNull();
  });

  it('says which version the conversation is held on', () => {
    expect(presentVersionPin(pinned)?.headline).toBe('This conversation is using version 4.1');
  });

  it('says a newer version exists', () => {
    expect(presentVersionPin(pinned)?.detail).toBe('Version 4.2 is available');
  });

  it('reassures that behaviour will not change', () => {
    expect(presentVersionPin(pinned)?.stable).toBe(true);
  });

  it('offers to move to the current version', () => {
    expect(presentVersionPin(pinned)?.action).toBe('update');
  });

  it('says plainly when a pin has been forced off', () => {
    const moved = {
      ...pinned,
      version: '4.2',
      outcome: 'pin-expired' as const,
      behaviourMayChange: true,
      reason: '3.9 is no longer supported',
    };
    expect(presentVersionPin(moved)?.headline).toBe('This conversation has moved to version 4.2');
  });

  it('gives the reason it was moved', () => {
    const moved = {
      ...pinned,
      outcome: 'pin-expired' as const,
      behaviourMayChange: true,
      reason: '3.9 is no longer supported',
    };
    expect(presentVersionPin(moved)?.detail).toBe('3.9 is no longer supported');
  });

  it('warns that answers may differ after a forced move', () => {
    const moved = { ...pinned, outcome: 'pin-expired' as const, behaviourMayChange: true, reason: 'x' };
    expect(presentVersionPin(moved)?.stable).toBe(false);
  });

  it('treats a forced move as worth noticing', () => {
    const moved = { ...pinned, outcome: 'pin-expired' as const, behaviourMayChange: true, reason: 'x' };
    expect(presentVersionPin(moved)?.severity).toBe('medium');
  });

  it('treats an ordinary pin as routine', () => {
    expect(presentVersionPin(pinned)?.severity).toBe('low');
  });

  it('has nothing to update to after a forced move', () => {
    const moved = { ...pinned, version: '4.2', outcome: 'pin-expired' as const, reason: 'x' };
    expect(presentVersionPin(moved)?.action).toBe('none');
  });

  it('says when a person chose the version rather than the system', () => {
    expect(presentVersionPin({ ...pinned, pinnedBy: 'ana' })?.chosenByPerson).toBe(true);
  });

  it('does not claim a person chose an automatic pin', () => {
    expect(presentVersionPin(pinned)?.chosenByPerson).toBe(false);
  });
});
