import { describe, expect, it } from 'vitest';

import { presentReport } from '@/lib/run-report-view';

const report = {
  outcome: 'done' as const,
  headline: 'Finished all 4 steps',
  took: '1m 30s',
  cost: '1.25',
  currency: 'USD',
  changes: ['file-written: out/report.md'],
  permanent: [] as string[],
  gaps: [] as string[],
  unsupported: [] as string[],
  reversible: true,
  needsAttention: false,
};

describe('presentReport', () => {
  it('leads with how the run ended', () => {
    expect(presentReport(report).headline).toBe('Finished all 4 steps');
  });

  it('shows what it cost and how long it took', () => {
    expect(presentReport(report).meta).toBe('1m 30s · $1.25');
  });

  it('omits the cost when it was free', () => {
    expect(presentReport({ ...report, cost: '0.00' }).meta).toBe('1m 30s');
  });

  it('lists what changed', () => {
    expect(presentReport(report).sections[0]).toEqual({
      title: 'Changed',
      items: ['file-written: out/report.md'],
      tone: 'neutral',
    });
  });

  it('calls out what cannot be undone', () => {
    const risky = { ...report, permanent: ['email-sent: ana'], reversible: false };
    expect(presentReport(risky).sections[1]).toEqual({
      title: 'Cannot be undone',
      items: ['email-sent: ana'],
      tone: 'warning',
    });
  });

  it('lists unanswered parts', () => {
    const partial = { ...report, outcome: 'partial' as const, gaps: ['who approves it'] };
    const section = presentReport(partial).sections.find((s) => s.title === 'Not answered');
    expect(section?.items).toEqual(['who approves it']);
  });

  it('lists unsupported claims separately from gaps', () => {
    const partial = {
      ...report,
      outcome: 'partial' as const,
      gaps: ['a'],
      unsupported: ['b'],
    };
    const titles = presentReport(partial).sections.map((s) => s.title);
    expect(titles).toContain('Not backed by a source');
  });

  it('shows no empty sections', () => {
    expect(presentReport(report).sections).toHaveLength(1);
  });

  it('offers to undo a reversible run', () => {
    expect(presentReport(report).action).toBe('undo');
  });

  it('offers to retry a failed run', () => {
    const failed = {
      ...report,
      outcome: 'failed' as const,
      headline: 'Stopped at gather, which failed',
      needsAttention: true,
      changes: [],
      reversible: false,
    };
    expect(presentReport(failed).action).toBe('retry');
  });

  it('offers nothing to undo when nothing changed', () => {
    const nothing = { ...report, changes: [], reversible: false };
    expect(presentReport(nothing).action).toBe('none');
  });

  it('marks a run needing attention', () => {
    const partial = { ...report, outcome: 'partial' as const, needsAttention: true, gaps: ['a'] };
    expect(presentReport(partial).severity).toBe('medium');
  });

  it('marks a failed run as serious', () => {
    const failed = { ...report, outcome: 'failed' as const, needsAttention: true };
    expect(presentReport(failed).severity).toBe('high');
  });

  it('marks a clean run as unremarkable', () => {
    expect(presentReport(report).severity).toBe('none');
  });
});
