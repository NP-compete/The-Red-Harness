import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  deleteWorkspaceFile,
  listWorkspaceFiles,
  readWorkspaceFile,
} from './workspace-files';

function answers(status: number, body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('listWorkspaceFiles', () => {
  it('lists what the agent wrote', async () => {
    answers(200, { files: [{ path: '/notes.md', bytes: 6, modified: '2026-10-27' }] });
    expect(await listWorkspaceFiles()).toEqual([
      { path: '/notes.md', bytes: 6, modified: '2026-10-27' },
    ]);
  });

  it('copes with a file the agent described oddly', async () => {
    answers(200, { files: [{ path: '/notes.md' }] });
    expect(await listWorkspaceFiles()).toEqual([
      { path: '/notes.md', bytes: 0, modified: '' },
    ]);
  });

  it('skips an entry with no path', async () => {
    answers(200, { files: [{ bytes: 3 }, { path: '/a.md', bytes: 1, modified: '' }] });
    expect((await listWorkspaceFiles()).map((f) => f.path)).toEqual(['/a.md']);
  });

  it('returns nothing when the agent will not say', async () => {
    answers(403, {});
    expect(await listWorkspaceFiles()).toEqual([]);
  });

  it('returns nothing when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await listWorkspaceFiles()).toEqual([]);
  });
});

describe('readWorkspaceFile', () => {
  it('hands back what the agent wrote', async () => {
    answers(200, { path: '/notes.md', content: 'Hello.' });
    expect(await readWorkspaceFile('/notes.md')).toBe('Hello.');
  });

  it('treats a file that is gone as nothing to show', async () => {
    answers(404, {});
    expect(await readWorkspaceFile('/notes.md')).toBeNull();
  });

  it('treats an empty file as empty, not as missing', async () => {
    answers(200, { path: '/notes.md', content: '' });
    expect(await readWorkspaceFile('/notes.md')).toBe('');
  });

  it('knows nothing when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await readWorkspaceFile('/notes.md')).toBeNull();
  });
});

describe('deleteWorkspaceFile', () => {
  it('reports a file that was removed', async () => {
    answers(204, {});
    expect(await deleteWorkspaceFile('/notes.md')).toBe(true);
  });

  it('reports a file that could not be removed', async () => {
    answers(404, {});
    expect(await deleteWorkspaceFile('/notes.md')).toBe(false);
  });

  it('reports a failure to reach the agent', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await deleteWorkspaceFile('/notes.md')).toBe(false);
  });
});
