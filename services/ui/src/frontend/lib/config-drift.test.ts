import { describe, expect, it } from 'vitest';

import { summariseDrift } from '@/lib/config-drift';

const baselineOnly = { path: 'runtime/agent.yaml', baseline: 'tokens: 20000' };

describe('summariseDrift', () => {
  it('reports nothing when every file comes from the pipeline', () => {
    const shown = summariseDrift([baselineOnly]);
    expect(shown.rows).toEqual([]);
    expect(shown.warning).toBeUndefined();
  });

  it('lists a file that was edited here', () => {
    const shown = summariseDrift([{ ...baselineOnly, overlay: 'tokens: 50000' }]);
    expect(shown.rows).toHaveLength(1);
    expect(shown.rows[0].path).toBe('runtime/agent.yaml');
    expect(shown.rows[0].current).toBe('tokens: 50000');
  });

  it('warns that edited files stop following the pipeline', () => {
    const shown = summariseDrift([{ ...baselineOnly, overlay: 'tokens: 50000' }]);
    expect(shown.warning).toContain('pipeline');
  });

  it('counts how many files have been taken over', () => {
    const shown = summariseDrift([
      { ...baselineOnly, overlay: 'tokens: 50000' },
      { path: 'PROMPT.md', baseline: 'a', overlay: 'b' },
      { path: 'mcp.json', baseline: 'c' },
    ]);
    expect(shown.count).toBe(2);
  });

  it('treats an edit identical to the pipeline as pinned rather than drifted', () => {
    const shown = summariseDrift([{ ...baselineOnly, overlay: 'tokens: 20000' }]);
    expect(shown.rows).toEqual([]);
    expect(shown.pinned).toEqual(['runtime/agent.yaml']);
  });

  it('offers to go back to the pipeline version, and to download the edit', () => {
    const shown = summariseDrift([{ ...baselineOnly, overlay: 'tokens: 50000' }]);
    expect(shown.rows[0].actions).toEqual(['adopt-baseline', 'export']);
  });

  it('still offers the export in a read-only deployment', () => {
    // Exporting is how a drifted deployment gets back: commit
    // the effective tree, reconcile, and the overrides can go.
    // This used to drop every action in read-only, which shut
    // the way out at the moment it was needed — a deployment
    // set back to read-only has not stopped being drifted, it
    // has stopped being able to edit.
    const shown = summariseDrift([{ ...baselineOnly, overlay: 'tokens: 50000' }], {
      readOnly: true,
    });
    expect(shown.rows[0].actions).toEqual(['export']);
  });

  it('offers no way to change anything in a read-only deployment', () => {
    const shown = summariseDrift([{ ...baselineOnly, overlay: 'tokens: 50000' }], {
      readOnly: true,
    });
    expect(shown.rows[0].actions).not.toContain('adopt-baseline');
  });

  it('says who changed it and when, where that is known', () => {
    const shown = summariseDrift([
      { ...baselineOnly, overlay: 'tokens: 50000', author: 'someone', at: '14:40' },
    ]);
    expect(shown.rows[0].author).toBe('someone');
    expect(shown.rows[0].at).toBe('14:40');
  });

  it('orders rows by path so the list does not jump about', () => {
    const shown = summariseDrift([
      { path: 'z.yaml', baseline: '1', overlay: '2' },
      { path: 'a.yaml', baseline: '1', overlay: '2' },
    ]);
    expect(shown.rows.map((row) => row.path)).toEqual(['a.yaml', 'z.yaml']);
  });

  it('handles a file that exists only as an edit', () => {
    const shown = summariseDrift([{ path: 'new.yaml', overlay: 'fresh' }]);
    expect(shown.rows[0].current).toBe('fresh');
    expect(shown.rows[0].baseline).toBeUndefined();
  });
});
