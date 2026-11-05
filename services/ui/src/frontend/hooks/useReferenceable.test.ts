import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useReferenceable } from './useReferenceable';

const files = vi.hoisted(() => ({ listWorkspaceFiles: vi.fn() }));
vi.mock('../services/workspace-files', () => files);

function answers(subagents: unknown[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ subagents }) }),
  );
}

beforeEach(() => {
  files.listWorkspaceFiles.mockResolvedValue([
    { path: '/notes.md', bytes: 1200, modified: '' },
  ]);
  answers([{ name: 'curator', description: 'Finds data worth trusting' }]);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe('useReferenceable', () => {
  it('offers the specialists the agent delegates to', async () => {
    const { result } = renderHook(() => useReferenceable());
    await waitFor(() =>
      expect(result.current.subagents.map((s) => s.name)).toEqual(['curator']),
    );
  });

  it('says what each specialist is for', async () => {
    const { result } = renderHook(() => useReferenceable());
    await waitFor(() =>
      expect(result.current.subagents[0].about).toBe('Finds data worth trusting'),
    );
  });

  it('offers the files the agent wrote, by the name a person would type', async () => {
    const { result } = renderHook(() => useReferenceable());
    await waitFor(() =>
      expect(result.current.documents.map((d) => d.name)).toEqual(['notes.md']),
    );
  });

  it('says how big a file is, so two similar names can be told apart', async () => {
    const { result } = renderHook(() => useReferenceable());
    await waitFor(() => expect(result.current.documents[0].about).toMatch(/1\.2 kB/));
  });

  it('offers nothing rather than failing when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    files.listWorkspaceFiles.mockResolvedValue([]);
    const { result } = renderHook(() => useReferenceable());
    await waitFor(() => expect(result.current.subagents).toEqual([]));
    expect(result.current.documents).toEqual([]);
  });

  it('still offers files when the specialists cannot be listed', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503 }));
    const { result } = renderHook(() => useReferenceable());
    await waitFor(() =>
      expect(result.current.documents.map((d) => d.name)).toEqual(['notes.md']),
    );
  });

  it('asks once rather than on every keystroke', async () => {
    const { result, rerender } = renderHook(() => useReferenceable());
    await waitFor(() => expect(result.current.subagents.length).toBe(1));
    // Counted before and after, rather than against a fixed
    // number. The hook draws on several sources and the
    // property is that rendering again asks nothing more —
    // not that there is exactly one request.
    const asked = vi.mocked(fetch).mock.calls.length;
    rerender();
    rerender();
    expect(vi.mocked(fetch).mock.calls.length).toBe(asked);
  });
});
