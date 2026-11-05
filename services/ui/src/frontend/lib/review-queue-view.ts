export interface SampledRun {
  runId: string;
  outcome: 'ok' | 'failed';
  ratedDown: boolean;
  at: string;
  reviewedBy: string | null;
  verdict: 'good' | 'bad' | null;
}

export interface ReviewRow {
  runId: string;
  because: string;
  when: string;
  status: string;
  action: 'review' | 'reopen';
}

export interface PresentedReviewQueue {
  rows: ReviewRow[];
  remaining: number;
  progress: string;
  verdicts: { good: number; bad: number };
  conclusion: string;
  emptyMessage: string;
}

export function presentReviewQueue(sample: SampledRun[], now: Date): PresentedReviewQueue {
  const rows = [...sample]
    .sort(
      (a, b) =>
        Number(a.reviewedBy !== null) - Number(b.reviewedBy !== null) ||
        Date.parse(b.at) - Date.parse(a.at),
    )
    .map((run) => ({
      runId: run.runId,
      // Saying why it was picked stops a sample reading as an accusation.
      because: run.ratedDown
        ? 'someone rated it down'
        : run.outcome === 'failed'
          ? 'it failed'
          : 'a sample of ordinary runs',
      when: ago(run.at, now),
      status: run.reviewedBy ? `reviewed by ${run.reviewedBy}` : 'waiting',
      action: run.reviewedBy ? ('reopen' as const) : ('review' as const),
    }));

  const reviewed = sample.filter((run) => run.reviewedBy !== null);
  const good = reviewed.filter((run) => run.verdict === 'good').length;
  const bad = reviewed.filter((run) => run.verdict === 'bad').length;

  return {
    rows,
    remaining: sample.length - reviewed.length,
    progress: `${reviewed.length} of ${sample.length} reviewed`,
    verdicts: { good, bad },
    // A partial sample is not a result; saying so invites the wrong conclusion.
    conclusion:
      sample.length > 0 && reviewed.length === sample.length
        ? `${good} of ${sample.length} judged good`
        : '',
    emptyMessage: sample.length === 0 ? 'Nothing to review' : '',
  };
}

function ago(at: string, now: Date): string {
  const hours = Math.round((now.getTime() - Date.parse(at)) / 3_600_000);
  if (hours < 1) return 'just now';
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}
