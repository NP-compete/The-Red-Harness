import { describe, expect, it } from 'vitest';

import { presentPreview } from '@/lib/dry-run-view';

const preview = {
  steps: [
    { tool: 'search', target: 'the web', harmless: true },
    { tool: 'write-file', target: 'out/report.md', harmless: false },
  ],
  wouldChange: 1,
  estimatedCost: '0.20',
  currency: 'USD',
  needsApproval: [] as string[],
  permanent: [] as string[],
  runnable: true,
  summary: '1 change, 1 read, about 0.20',
  reason: '',
};

describe('presentPreview', () => {
  it('makes clear nothing has happened yet', () => {
    expect(presentPreview(preview).headline).toBe('Nothing has run yet');
  });

  it('shows what would happen', () => {
    expect(presentPreview(preview).detail).toBe('1 change, 1 read, about 0.20');
  });

  it('marks the steps that would change something', () => {
    const rows = presentPreview(preview).rows;
    expect(rows.map((row) => row.changes)).toEqual([false, true]);
  });

  it('describes each step plainly', () => {
    expect(presentPreview(preview).rows[1].label).toBe('write-file → out/report.md');
  });

  it('shows the estimated cost as money', () => {
    expect(presentPreview(preview).cost).toBe('about $0.20');
  });

  it('shows no cost when it would cost nothing', () => {
    expect(presentPreview({ ...preview, estimatedCost: '0.00' }).cost).toBe('');
  });

  it('can be run when nothing is blocking it', () => {
    expect(presentPreview(preview).canRun).toBe(true);
  });

  it('cannot be run while approval is outstanding', () => {
    const blocked = {
      ...preview,
      needsApproval: ['deploy: production'],
      runnable: false,
      reason: 'some steps need approval before this can run',
    };
    expect(presentPreview(blocked).canRun).toBe(false);
  });

  it('says what needs approving', () => {
    const blocked = { ...preview, needsApproval: ['deploy: production'], runnable: false, reason: 'x' };
    expect(presentPreview(blocked).approvals).toEqual(['deploy: production']);
  });

  it('warns about steps that could not be undone', () => {
    const risky = { ...preview, permanent: ['send-email: ana'] };
    expect(presentPreview(risky).warning).toBe('1 of these cannot be undone afterwards');
  });

  it('does not warn when everything could be undone', () => {
    expect(presentPreview(preview).warning).toBe('');
  });

  it('treats permanent steps as worth a closer look', () => {
    const risky = { ...preview, permanent: ['send-email: ana'] };
    expect(presentPreview(risky).severity).toBe('medium');
  });

  it('treats a reversible preview as routine', () => {
    expect(presentPreview(preview).severity).toBe('info');
  });

  it('says plainly when a preview would change nothing at all', () => {
    const readOnly = { ...preview, wouldChange: 0, summary: 'nothing would change' };
    expect(presentPreview(readOnly).detail).toBe('nothing would change');
  });
});
