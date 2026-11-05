export interface GuestState {
  isGuest: boolean;
  mayWrite: boolean;
  daysLeft: number;
  expired: boolean;
  organisation: string;
}

export interface PresentedGuestBanner {
  headline: string;
  detail: string;
  expiry: string;
  dismissible: boolean;
  severity: 'info' | 'medium' | 'high';
}

function expiryText(state: GuestState): string {
  if (state.expired) {
    return 'Your access has ended';
  }
  if (state.daysLeft === 0) {
    return 'Your access ends today';
  }
  return `Your access ends in ${state.daysLeft} day${state.daysLeft === 1 ? '' : 's'}`;
}

export function presentGuestBanner(state: GuestState): PresentedGuestBanner | null {
  if (!state.isGuest) {
    return null;
  }

  let severity: PresentedGuestBanner['severity'] = 'info';
  if (state.expired) {
    severity = 'high';
  } else if (state.daysLeft <= 1) {
    severity = 'medium';
  }

  return {
    headline: `You are a guest in ${state.organisation}'s workspace`,
    detail: `You can ${state.mayWrite ? 'see' : 'read'} this conversation and nothing else`,
    expiry: expiryText(state),
    // Where you are and what you can reach is not a notice to wave away.
    dismissible: false,
    severity,
  };
}
