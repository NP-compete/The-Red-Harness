export type ResultVerdict = 'accepted' | 'unsourced' | 'empty' | 'failed';

export interface ResultState {
  child: string;
  verdict: ResultVerdict;
  answer: string;
  sources: string[];
  cost: string;
  trusted: boolean;
  worthRetrying: boolean;
  reason: string;
}

export interface PresentedResult {
  headline: string;
  answer: string;
  sources: string[];
  cost: string;
  note: string;
  quoted: boolean;
  retry: boolean;
  severity: 'info' | 'low' | 'medium';
}

const HEADLINE: Record<ResultVerdict, string> = {
  accepted: 'answered',
  unsourced: 'answered',
  empty: 'returned nothing',
  failed: 'could not finish',
};

export function presentResult(result: ResultState): PresentedResult {
  const note =
    result.verdict === 'unsourced' ? 'This answer cites nothing' : result.reason;

  let severity: PresentedResult['severity'] = 'info';
  if (result.verdict === 'failed' || !result.trusted) {
    severity = 'medium';
  } else if (result.verdict === 'unsourced' || result.verdict === 'empty') {
    severity = 'low';
  }

  return {
    headline: `${result.child} ${HEADLINE[result.verdict]}`,
    answer: result.answer,
    sources: result.sources,
    cost: `$${result.cost}`,
    note: result.verdict === 'accepted' ? '' : note,
    // Work built on untrusted material is shown as something read, not followed.
    quoted: !result.trusted,
    retry: result.worthRetrying,
    severity,
  };
}
