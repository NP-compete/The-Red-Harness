export interface AllowlistState {
  ranges: string[];
  enforced: boolean;
  breakGlassRoles: string[];
  wouldRefuseCount: number;
}

export interface PresentedAllowlist {
  ranges: string[];
  status: string;
  impact: string;
  warning: string;
  breakGlass: string;
}

export type BlockReason = 'not-allowed' | 'unreadable';

export interface PresentedBlock {
  headline: string;
  detail: string;
  action: 'contact-admin';
}

export function presentAllowlist(allowlist: AllowlistState): PresentedAllowlist {
  const locked = allowlist.wouldRefuseCount;

  return {
    ranges: allowlist.ranges,
    status: allowlist.enforced ? 'Enforced' : 'Not enforced — watching only',
    impact: allowlist.enforced
      ? ''
      : locked > 0
        ? `${locked} sign-ins would have been refused`
        : 'Nobody would have been refused',
    warning: warning(allowlist, locked),
    breakGlass:
      allowlist.breakGlassRoles.length === 0
        ? 'Nobody can bypass this'
        : `${allowlist.breakGlassRoles.join(', ')} can still sign in from anywhere`,
  };
}

function warning(allowlist: AllowlistState, locked: number): string {
  // An enforced list with nothing in it is a lockout waiting to be noticed.
  if (allowlist.ranges.length === 0) return 'No ranges are listed, so nobody can sign in';
  if (!allowlist.enforced && locked > 0) {
    return `Turning this on now would lock out ${locked} recent sign-ins`;
  }
  return '';
}

export function presentBlockedSource(reason: BlockReason): PresentedBlock {
  if (reason === 'unreadable') {
    return {
      headline: 'Your connection could not be checked',
      detail: '',
      action: 'contact-admin',
    };
  }

  return {
    headline: 'You cannot sign in from this network',
    // Which ranges are permitted is not something a refused caller needs.
    detail: '',
    action: 'contact-admin',
  };
}
