import { describe, expect, it } from 'vitest';

import { presentSignIn } from '@/lib/sign-in-check-view';

const allowed = {
  outcome: 'allowed' as const,
  stepUp: false,
  readOnly: false,
  exceptional: false,
  notify: false,
  reason: '',
};

describe('presentSignIn', () => {
  it('shows nothing for an ordinary sign-in', () => {
    expect(presentSignIn(allowed)).toBeNull();
  });

  it('asks for more proof when the sign-in looks unfamiliar', () => {
    const challenge = {
      ...allowed,
      outcome: 'step-up' as const,
      stepUp: true,
      notify: true,
      reason: 'this sign-in does not look like your usual one',
    };
    expect(presentSignIn(challenge)?.headline).toBe('Confirm it is you');
  });

  it('explains why the extra proof is needed', () => {
    const challenge = {
      ...allowed,
      outcome: 'step-up' as const,
      stepUp: true,
      reason: 'this sign-in does not look like your usual one',
    };
    expect(presentSignIn(challenge)?.detail).toBe(
      'this sign-in does not look like your usual one',
    );
  });

  it('does not say the person was blocked when only proof is needed', () => {
    const challenge = { ...allowed, outcome: 'step-up' as const, stepUp: true, reason: 'x' };
    expect(presentSignIn(challenge)?.blocked).toBe(false);
  });

  it('says plainly when a sign-in was refused', () => {
    const refused = {
      ...allowed,
      outcome: 'refused' as const,
      notify: true,
      reason: 'you cannot sign in from this network',
    };
    expect(presentSignIn(refused)?.headline).toBe('You cannot sign in');
  });

  it('marks a refusal as blocking', () => {
    const refused = { ...allowed, outcome: 'refused' as const, reason: 'x' };
    expect(presentSignIn(refused)?.blocked).toBe(true);
  });

  it('says plainly when someone is in but can do nothing', () => {
    const seatless = { ...allowed, readOnly: true };
    expect(presentSignIn(seatless)?.headline).toBe('You are signed in but have no seat');
  });

  it('tells a seatless person what to do', () => {
    const seatless = { ...allowed, readOnly: true };
    expect(presentSignIn(seatless)?.action).toBe('request-seat');
  });

  it('offers a way to confirm identity', () => {
    const challenge = { ...allowed, outcome: 'step-up' as const, stepUp: true, reason: 'x' };
    expect(presentSignIn(challenge)?.action).toBe('confirm');
  });

  it('offers help when refused', () => {
    const refused = { ...allowed, outcome: 'refused' as const, reason: 'x' };
    expect(presentSignIn(refused)?.action).toBe('contact-admin');
  });

  it('notes when the sign-in was allowed by exception', () => {
    const unusual = { ...allowed, exceptional: true, notify: true };
    expect(presentSignIn(unusual)?.note).toBe('This sign-in was allowed as an exception');
  });

  it('has no such note for an ordinary allowed sign-in', () => {
    const seatless = { ...allowed, readOnly: true };
    expect(presentSignIn(seatless)?.note).toBe('');
  });

  it('treats a refusal as serious', () => {
    const refused = { ...allowed, outcome: 'refused' as const, reason: 'x' };
    expect(presentSignIn(refused)?.severity).toBe('high');
  });

  it('treats a challenge as routine', () => {
    const challenge = { ...allowed, outcome: 'step-up' as const, stepUp: true, reason: 'x' };
    expect(presentSignIn(challenge)?.severity).toBe('info');
  });
});
