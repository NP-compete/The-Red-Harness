import { describe, expect, it } from 'vitest';

import { highlightClaims } from '@/lib/claim-highlight';

const answer =
  'Expenses over 500 need approval. Reimbursement takes three days. Travel is booked centrally.';

const claims = [
  { text: 'Expenses over 500 need approval.', supported: true, contradicted: false },
  { text: 'Reimbursement takes three days.', supported: false, contradicted: false },
  { text: 'Travel is booked centrally.', supported: false, contradicted: true },
];

describe('highlightClaims', () => {
  it('covers the whole answer with segments', () => {
    const segments = highlightClaims(answer, claims);
    expect(segments.map((segment) => segment.text).join('')).toBe(answer);
  });

  it('marks a supported claim as supported', () => {
    const segments = highlightClaims(answer, claims);
    expect(segments.find((segment) => segment.text.startsWith('Expenses'))?.status).toBe(
      'supported',
    );
  });

  it('marks an unsupported claim as unsupported', () => {
    const segments = highlightClaims(answer, claims);
    expect(segments.find((segment) => segment.text.startsWith('Reimbursement'))?.status).toBe(
      'unsupported',
    );
  });

  it('marks a contradicting claim as contradicted', () => {
    const segments = highlightClaims(answer, claims);
    expect(segments.find((segment) => segment.text.startsWith('Travel'))?.status).toBe(
      'contradicted',
    );
  });

  it('leaves text between claims unmarked', () => {
    const segments = highlightClaims('Hello. Expenses over 500 need approval.', [claims[0]]);
    expect(segments[0]).toEqual({ text: 'Hello. ', status: 'plain' });
  });

  it('keeps the segments in reading order', () => {
    const segments = highlightClaims(answer, claims);
    const marked = segments.filter((segment) => segment.status !== 'plain');
    expect(marked.map((segment) => segment.text[0])).toEqual(['E', 'R', 'T']);
  });

  it('ignores a claim that does not appear in the answer', () => {
    const segments = highlightClaims(answer, [
      { text: 'Something never written.', supported: false, contradicted: false },
    ]);
    expect(segments).toEqual([{ text: answer, status: 'plain' }]);
  });

  it('handles an answer with no claims at all', () => {
    expect(highlightClaims(answer, [])).toEqual([{ text: answer, status: 'plain' }]);
  });

  it('handles an empty answer', () => {
    expect(highlightClaims('', claims)).toEqual([]);
  });

  it('does not overlap segments when one claim contains another', () => {
    const nested = [
      { text: 'Expenses over 500 need approval.', supported: true, contradicted: false },
      { text: 'over 500', supported: false, contradicted: false },
    ];
    const segments = highlightClaims(answer, nested);
    expect(segments.map((segment) => segment.text).join('')).toBe(answer);
  });

  it('prefers the longer claim when two overlap', () => {
    const nested = [
      { text: 'over 500', supported: false, contradicted: false },
      { text: 'Expenses over 500 need approval.', supported: true, contradicted: false },
    ];
    const segments = highlightClaims(answer, nested);
    expect(segments[0]).toEqual({
      text: 'Expenses over 500 need approval.',
      status: 'supported',
    });
  });

  it('counts how much of the answer is marked as a problem', () => {
    const segments = highlightClaims(answer, claims);
    const problem = segments.filter((segment) => segment.status !== 'plain' && segment.status !== 'supported');
    expect(problem).toHaveLength(2);
  });
});
