export interface EgressPolicy {
  allowedHosts: string[];
  deniedHosts: string[];
  allowPrivateAddresses: boolean;
}

export interface HostRow {
  host: string;
  allowed: boolean;
  note: string;
}

export type BlockVerdict = 'not-allowed' | 'denied' | 'private-address' | 'bad-scheme';

export interface BlockedRequest {
  host: string;
  verdict: BlockVerdict;
}

export interface PresentedBlock {
  headline: string;
  succeeded: false;
  action: 'request-access' | 'none';
}

export function presentReachableHosts(policy: EgressPolicy): HostRow[] {
  return [
    ...policy.allowedHosts.map((host) => ({ host, allowed: true, note: note(host) })),
    ...policy.deniedHosts.map((host) => ({
      host,
      allowed: false,
      note: 'blocked, even though a wildcard would otherwise allow it',
    })),
  ];
}

function note(host: string): string {
  return host.startsWith('*.')
    ? `and anything below it, but not ${host.slice(2)} itself`
    : '';
}

export function presentBlockedRequest(blocked: BlockedRequest): PresentedBlock {
  const headlines: Record<BlockVerdict, string> = {
    'not-allowed': `${blocked.host} is not on the list of hosts this agent can reach`,
    denied: `${blocked.host} is deliberately blocked for this agent`,
    'private-address': `${blocked.host} is on the internal network, which agents cannot reach`,
    'bad-scheme': 'That is not a web address, so it was not fetched',
  };

  return {
    headline: headlines[blocked.verdict],
    succeeded: false,
    // Only an oversight is worth asking about; the rest are decisions.
    action: blocked.verdict === 'not-allowed' ? 'request-access' : 'none',
  };
}
