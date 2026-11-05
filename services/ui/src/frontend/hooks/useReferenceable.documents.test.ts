/**
 * A person's own documents belong in the `#` list.
 *
 * `#` offered the files the agent had written and nothing a
 * person had uploaded — so the one document somebody most
 * wants to point at, the one they added themselves an hour
 * ago, was the one the shorthand could not name.
 *
 * Both lists are things they can already open elsewhere, so
 * the shorthand still reaches nothing new. That is the rule
 * this must not break: the library returns only what this
 * person may see, and nothing here widens it.
 */

import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useReferenceable } from './useReferenceable';
import * as workspace from '../services/workspace-files';
import * as library from '../services/knowledge-api';

function answering(documents: unknown) {
  vi.spyOn(workspace, 'listWorkspaceFiles').mockResolvedValue([
    { path: '/report.md', bytes: 2048 },
  ] as never);
  vi.spyOn(library, 'readLibrary').mockResolvedValue(
    documents === null ? null : ({ documents, team: [] } as never),
  );
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ subagents: [] }) }),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('the documents a person can name', () => {
  it('includes what they uploaded', async () => {
    answering([{ id: 'user:1', title: 'Spending limits', bytes: 62 }]);
    const { result } = renderHook(() => useReferenceable());
    await waitFor(() =>
      expect(result.current.documents.map((d) => d.name)).toContain(
        'Spending limits',
      ),
    );
  });

  it('still includes what the agent wrote', async () => {
    // Both, not one replacing the other.
    answering([{ id: 'user:1', title: 'Spending limits', bytes: 62 }]);
    const { result } = renderHook(() => useReferenceable());
    await waitFor(() =>
      expect(result.current.documents.map((d) => d.name)).toContain('report.md'),
    );
  });

  it('says where a document came from, so two names are not confusable', async () => {
    // A file the agent wrote and a document somebody uploaded
    // can share a name, and picking the wrong one is silent.
    answering([{ id: 'user:1', title: 'Spending limits', bytes: 62 }]);
    const { result } = renderHook(() => useReferenceable());
    await waitFor(() => expect(result.current.documents.length).toBe(2));
    const mine = result.current.documents.find(
      (d) => d.name === 'Spending limits',
    );
    expect(mine?.about).toBeTruthy();
  });

  it('a document with no title falls back to something nameable', async () => {
    answering([{ id: 'user:7', title: '', bytes: 10 }]);
    const { result } = renderHook(() => useReferenceable());
    await waitFor(() => expect(result.current.documents.length).toBe(2));
    expect(result.current.documents.every((d) => d.name)).toBe(true);
  });
});

describe('when the library is not there', () => {
  it('the workspace files still arrive', async () => {
    // A deployment that keeps no personal documents is the
    // normal case, and it must not cost the other list.
    answering(null);
    const { result } = renderHook(() => useReferenceable());
    await waitFor(() =>
      expect(result.current.documents.map((d) => d.name)).toEqual(['report.md']),
    );
  });

  it('a library that fails does not cost the workspace files', async () => {
    vi.spyOn(workspace, 'listWorkspaceFiles').mockResolvedValue([
      { path: '/report.md', bytes: 2048 },
    ] as never);
    vi.spyOn(library, 'readLibrary').mockRejectedValue(new Error('down'));
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ subagents: [] }) }),
    );

    const { result } = renderHook(() => useReferenceable());
    await waitFor(() =>
      expect(result.current.documents.map((d) => d.name)).toEqual(['report.md']),
    );
  });

  it('workspace files failing does not cost the library', async () => {
    vi.spyOn(workspace, 'listWorkspaceFiles').mockRejectedValue(new Error('down'));
    vi.spyOn(library, 'readLibrary').mockResolvedValue({
      documents: [{ id: 'user:1', title: 'Spending limits', bytes: 62 }],
      team: [],
    } as never);
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ subagents: [] }) }),
    );

    const { result } = renderHook(() => useReferenceable());
    await waitFor(() =>
      expect(result.current.documents.map((d) => d.name)).toEqual([
        'Spending limits',
      ]),
    );
  });
});

describe("a team's documents", () => {
  it('can be named too', async () => {
    // Listed read-only on the documents page, so a person
    // can already see them; leaving them out of the
    // shorthand would be an inconsistency, not a rule.
    vi.spyOn(workspace, 'listWorkspaceFiles').mockResolvedValue([] as never);
    vi.spyOn(library, 'readLibrary').mockResolvedValue({
      documents: [],
      team: [{ id: 'team:1', title: 'Platform handbook', bytes: 900, team: 'platform' }],
    } as never);
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ subagents: [] }) }),
    );

    const { result } = renderHook(() => useReferenceable());
    await waitFor(() =>
      expect(result.current.documents.map((d) => d.name)).toContain(
        'Platform handbook',
      ),
    );
  });
});
