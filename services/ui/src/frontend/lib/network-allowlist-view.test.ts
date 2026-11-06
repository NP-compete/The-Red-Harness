import { describe, expect, it } from 'vitest';

import { presentAllowlist, presentBlockedSource } from '@/lib/network-allowlist-view';

const allowlist = {
  ranges: ['203.0.113.0/24', '2001:db8::/32'],
  enforced: true,
  breakGlassRoles: ['platform-admin'],
  wouldRefuseCount: 0,
};

describe('presentAllowlist', () => {
  it('lists the permitted ranges', () => {
    expect(presentAllowlist(allowlist).ranges).toEqual(['203.0.113.0/24', '2001:db8::/32']);
  });

  it('says the rule is being applied', () => {
    expect(presentAllowlist(allowlist).status).toBe('Enforced');
  });

  it('says plainly when the rule is only being watched', () => {
    const watching = { ...allowlist, enforced: false, wouldRefuseCount: 12 };
    expect(presentAllowlist(watching).status).toBe('Not enforced — watching only');
  });

  it('says how many would be refused if it were turned on', () => {
    const watching = { ...allowlist, enforced: false, wouldRefuseCount: 12 };
    expect(presentAllowlist(watching).impact).toBe('12 sign-ins would have been refused');
  });

  it('says nobody would be affected when that is true', () => {
    const watching = { ...allowlist, enforced: false, wouldRefuseCount: 0 };
    expect(presentAllowlist(watching).impact).toBe('Nobody would have been refused');
  });

  it('shows no impact figure once it is enforced', () => {
    expect(presentAllowlist(allowlist).impact).toBe('');
  });

  it('warns loudly before enforcing something that would lock people out', () => {
    const watching = { ...allowlist, enforced: false, wouldRefuseCount: 12 };
    expect(presentAllowlist(watching).warning).toBe(
      'Turning this on now would lock out 12 recent sign-ins',
    );
  });

  it('does not warn when enforcing would affect nobody', () => {
    const watching = { ...allowlist, enforced: false, wouldRefuseCount: 0 };
    expect(presentAllowlist(watching).warning).toBe('');
  });

  it('names who could still get in from elsewhere', () => {
    expect(presentAllowlist(allowlist).breakGlass).toBe(
      'platform-admin can still sign in from anywhere',
    );
  });

  it('says plainly when nobody has a way round it', () => {
    const strict = { ...allowlist, breakGlassRoles: [] };
    expect(presentAllowlist(strict).breakGlass).toBe('Nobody can bypass this');
  });

  it('refuses to show an empty enforced list as safe', () => {
    const empty = { ...allowlist, ranges: [] };
    expect(presentAllowlist(empty).warning).toBe('No ranges are listed, so nobody can sign in');
  });
});

describe('presentBlockedSource', () => {
  it('says plainly that the network is not permitted', () => {
    expect(presentBlockedSource('not-allowed').headline).toBe(
      'You cannot sign in from this network',
    );
  });

  it('gives no detail about which ranges are allowed', () => {
    expect(presentBlockedSource('not-allowed').detail).toBe('');
  });

  it('tells the person who can help', () => {
    expect(presentBlockedSource('not-allowed').action).toBe('contact-admin');
  });

  it('explains an unreadable address differently', () => {
    expect(presentBlockedSource('unreadable').headline).toBe('Your connection could not be checked');
  });
});
