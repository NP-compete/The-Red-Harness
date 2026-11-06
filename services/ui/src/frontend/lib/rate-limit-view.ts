export interface RateLimitState {
  allowed: boolean;
  remaining: number;
  burst: number;
  retryAfter: number;
  reason: string;
}

export interface PresentedRateLimit {
  /** Catalogue keys, not words: this runs where there is no
   *  translator, and a sentence built here would be English in
   *  every language. `count` is what the plural turns on. */
  headline: string;
  detail: string;
  count: number;
  severity: 'low' | 'high';
  canSend: boolean;
  retryAfterSeconds: number;
}

const WARN_AT = 1;

export function presentRateLimit(state: RateLimitState): PresentedRateLimit | null {
  if (!state.allowed) {
    // Rounded up, so acting on the stated wait is always long enough.
    const seconds = Math.max(1, Math.ceil(state.retryAfter));
    return {
      headline: 'rateLimit.tooMany',
      detail: 'rateLimit.tryAgain',
      count: seconds,
      severity: 'high',
      canSend: false,
      retryAfterSeconds: seconds,
    };
  }

  if (state.remaining > WARN_AT) return null;

  return {
    headline: 'rateLimit.slowDown',
    detail: '',
    count: state.remaining,
    severity: 'low',
    canSend: true,
    retryAfterSeconds: 0,
  };
}
