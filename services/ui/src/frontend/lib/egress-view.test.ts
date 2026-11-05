import { describe, expect, it } from 'vitest';

import { presentBlockedRequest, presentReachableHosts } from '@/lib/egress-view';

const policy = {
  allowedHosts: ['api.example.com', '*.internal.example.com'],
  deniedHosts: ['secrets.internal.example.com'],
  allowPrivateAddresses: false,
};

describe('presentReachableHosts', () => {
  it('lists each host this agent can reach', () => {
    const rows = presentReachableHosts(policy);
    expect(rows.map((row) => row.host)).toEqual([
      'api.example.com',
      '*.internal.example.com',
      'secrets.internal.example.com',
    ]);
  });

  it('says a wildcard covers subdomains only', () => {
    const [, wildcard] = presentReachableHosts(policy);
    expect(wildcard.note).toBe('and anything below it, but not internal.example.com itself');
  });

  it('marks a denied host as denied even though it matches a wildcard', () => {
    const denied = presentReachableHosts(policy).at(-1);
    expect(denied?.allowed).toBe(false);
  });

  it('says the private network is out of reach', () => {
    expect(presentReachableHosts(policy).some((row) => row.host === 'anything else')).toBe(false);
    expect(presentReachableHosts(policy).length).toBe(3);
  });

  it('says plainly when an agent can reach nothing', () => {
    const closed = { ...policy, allowedHosts: [], deniedHosts: [] };
    expect(presentReachableHosts(closed)).toEqual([]);
  });
});

describe('presentBlockedRequest', () => {
  it('names the host that was refused', () => {
    const shown = presentBlockedRequest({ host: 'api.other.com', verdict: 'not-allowed' });
    expect(shown.headline).toBe('api.other.com is not on the list of hosts this agent can reach');
  });

  it('distinguishes a deliberate denial from an unlisted host', () => {
    const shown = presentBlockedRequest({ host: 'secrets.internal.example.com', verdict: 'denied' });
    expect(shown.headline).toContain('deliberately blocked');
  });

  it('explains a private address refusal without jargon', () => {
    const shown = presentBlockedRequest({ host: '169.254.169.254', verdict: 'private-address' });
    expect(shown.headline).toContain('internal network');
  });

  it('explains a bad scheme', () => {
    const shown = presentBlockedRequest({ host: '', verdict: 'bad-scheme' });
    expect(shown.headline).toContain('web address');
  });

  it('offers to ask for the host to be added when it is merely unlisted', () => {
    const shown = presentBlockedRequest({ host: 'api.other.com', verdict: 'not-allowed' });
    expect(shown.action).toBe('request-access');
  });

  it('offers nothing when the host was deliberately blocked', () => {
    const shown = presentBlockedRequest({ host: 'secrets.internal.example.com', verdict: 'denied' });
    expect(shown.action).toBe('none');
  });

  it('offers nothing for a private address', () => {
    const shown = presentBlockedRequest({ host: '10.0.0.5', verdict: 'private-address' });
    expect(shown.action).toBe('none');
  });

  it('never suggests the request succeeded', () => {
    const verdicts = ['not-allowed', 'denied', 'private-address', 'bad-scheme'] as const;
    for (const verdict of verdicts) {
      expect(presentBlockedRequest({ host: 'h', verdict }).succeeded).toBe(false);
    }
  });
});
