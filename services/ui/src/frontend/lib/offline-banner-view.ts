export interface ConnectionState {
  connected: boolean;
  warn: boolean;
  queued: number;
  runOutcomeUnknown: boolean;
  secondsDown: number;
}

export interface PresentedOfflineBanner {
  /** Catalogue keys, not words: this runs where there is no
   *  translator, and a banner shown when the connection drops is
   *  the last place to fall back to one language. */
  headline: string;
  detail: string;
  queued: number;
  warning: string;
  actions: string[];
  dismissible: boolean;
  severity: 'medium' | 'high';
}

export function presentOfflineBanner(state: ConnectionState): PresentedOfflineBanner | null {
  // A blip is not worth a banner; saying so would be the interruption.
  if (state.connected || !state.warn) {
    return null;
  }

  return {
    headline: 'offline.noConnection',
    detail: state.queued > 0 ? 'offline.queued' : '',
    queued: state.queued,
    warning: state.runOutcomeUnknown ? 'offline.runUnknown' : '',
    actions: ['offline.retryNow'],
    dismissible: false,
    severity: state.runOutcomeUnknown ? 'high' : 'medium',
  };
}
