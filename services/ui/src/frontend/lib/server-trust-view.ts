export type TrustVerdict =
  | 'unchanged'
  | 'unknown'
  | 'moved'
  | 'certificate-changed'
  | 'tools-changed'
  | 'insecure';

export interface ServerCheck {
  name: string;
  trust: TrustVerdict;
  usable: boolean;
  reason: string;
}

export interface PresentedServerTrust {
  headline: string;
  detail: string;
  severity: 'none' | 'low' | 'medium' | 'high';
  inUse: boolean;
  action: 'confirm' | 'none';
  secondaryAction: 'disconnect' | 'none';
}

const HEADLINES: Record<TrustVerdict, (name: string) => string> = {
  unchanged: (name) => name,
  unknown: (name) => `${name} has not been connected before`,
  moved: (name) => `${name} is answering from a different address`,
  'certificate-changed': (name) => `${name} may not be the server you trusted`,
  'tools-changed': (name) => `${name} offers a different set of tools`,
  insecure: (name) => `${name} is not using an encrypted connection`,
};

const SEVERE = new Set<TrustVerdict>(['certificate-changed', 'insecure']);

export function presentServerTrust(check: ServerCheck): PresentedServerTrust {
  return {
    headline: HEADLINES[check.trust](check.name),
    detail: check.reason,
    severity: severity(check),
    inUse: check.usable,
    action: check.usable ? 'none' : 'confirm',
    // Only offered where the server might be a different one altogether.
    secondaryAction: SEVERE.has(check.trust) ? 'disconnect' : 'none',
  };
}

function severity(check: ServerCheck): PresentedServerTrust['severity'] {
  if (SEVERE.has(check.trust)) return 'high';
  if (check.trust === 'unchanged') return 'none';
  return check.usable ? 'low' : 'medium';
}
