export interface HighlightableClaim {
  text: string;
  supported: boolean;
  contradicted: boolean;
}

export type SegmentStatus = 'plain' | 'supported' | 'unsupported' | 'contradicted';

export interface Segment {
  text: string;
  status: SegmentStatus;
}

export function highlightClaims(answer: string, claims: HighlightableClaim[]): Segment[] {
  if (answer === '') return [];

  const spans = [...claims]
    // Longest first, so a claim nested inside another does not split it.
    .sort((a, b) => b.text.length - a.text.length)
    .map((claim) => ({ claim, at: answer.indexOf(claim.text) }))
    .filter(({ at }) => at !== -1)
    .reduce<{ start: number; end: number; status: SegmentStatus }[]>((taken, { claim, at }) => {
      const end = at + claim.text.length;
      const overlaps = taken.some((span) => at < span.end && end > span.start);
      return overlaps ? taken : [...taken, { start: at, end, status: statusOf(claim) }];
    }, [])
    .sort((a, b) => a.start - b.start);

  const segments: Segment[] = [];
  let cursor = 0;

  for (const span of spans) {
    if (span.start > cursor) {
      segments.push({ text: answer.slice(cursor, span.start), status: 'plain' });
    }
    segments.push({ text: answer.slice(span.start, span.end), status: span.status });
    cursor = span.end;
  }

  if (cursor < answer.length) {
    segments.push({ text: answer.slice(cursor), status: 'plain' });
  }

  return segments;
}

function statusOf(claim: HighlightableClaim): SegmentStatus {
  if (claim.contradicted) return 'contradicted';
  return claim.supported ? 'supported' : 'unsupported';
}
