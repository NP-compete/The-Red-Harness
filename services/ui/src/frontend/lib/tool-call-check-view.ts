export interface CallCheck {
  permitted: boolean;
  faults: string[];
  retryable: boolean;
  reason: string;
  tool: string;
}

export interface PresentedCallCheck {
  headline: string;
  detail: string;
  problems: string[];
  willRetry: boolean;
  ran: false;
  severity: 'info' | 'medium' | 'high';
  action: 'review-connection' | 'none';
}

const WORDS: Record<string, string> = {
  'server-untrusted': 'The server is not the one that was trusted',
  'shape-changed': 'This tool has changed since it was approved',
  'bad-arguments': 'The arguments do not fit this tool',
  'no-credential': 'There is no credential set up for this',
  'destination-blocked': 'That address is not one this agent may reach',
  'rate-limited': 'This is being called too often',
  'too-many-at-once': 'Too many of these are already running',
};

// Something may not be what it claims to be; that outranks a fixable mistake.
const TRUST_FAULTS = new Set(['server-untrusted', 'shape-changed']);

export function presentCallCheck(check: CallCheck): PresentedCallCheck | null {
  if (check.permitted) return null;

  const trust = check.faults.some((fault) => TRUST_FAULTS.has(fault));

  return {
    headline: `${check.tool} was not run`,
    detail: check.reason,
    problems: check.faults.map((fault) => WORDS[fault] ?? fault),
    willRetry: check.retryable,
    ran: false,
    severity: trust ? 'high' : check.retryable ? 'info' : 'medium',
    action: trust ? 'review-connection' : 'none',
  };
}
