export interface IngestionResult {
  name: string;
  permitted: boolean;
  refusal: string | null;
  retryAfterScan: boolean;
  reason: string;
}

export interface PresentedIngestion {
  headline: string;
  detail: string;
  willRetry: boolean;
  severity: 'info' | 'medium' | 'high';
  action: 'scrub' | 'split' | 'none';
}

const FIXABLE: Record<string, PresentedIngestion['action']> = {
  'personal-data': 'scrub',
  'too-large': 'split',
};

export function presentIngestion(result: IngestionResult): PresentedIngestion | null {
  if (result.permitted) return null;

  const waiting = result.retryAfterScan;
  const unsafe = result.refusal === 'unsafe';

  return {
    headline: waiting
      ? `${result.name} is still being checked`
      : `${result.name} was not added`,
    detail: result.reason,
    willRetry: waiting,
    severity: unsafe ? 'high' : waiting ? 'info' : 'medium',
    // Only offered where the person can actually change the outcome.
    action: waiting ? 'none' : (FIXABLE[result.refusal ?? ''] ?? 'none'),
  };
}
