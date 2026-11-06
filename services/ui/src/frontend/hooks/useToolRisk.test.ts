import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useToolRisk } from './useToolRisk';

const answer = vi.hoisted(() => ({ ok: true, body: {} as unknown }));

beforeEach(() => {
  answer.ok = true;
  answer.body = {
    approval: {
      tools: {
        search: { decision: 'allow', risk: 'low', reason: '' },
        send_email: { decision: 'interrupt', risk: 'high', reason: 'writes to the world' },
        delete_everything: { decision: 'deny', risk: 'high', reason: 'never' },
      },
    },
  };
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(() =>
      Promise.resolve({ ok: answer.ok, json: () => Promise.resolve(answer.body) }),
    ),
  );
});

describe('useToolRisk', () => {
  it('treats a tool the policy waves through as reversible', async () => {
    const { result } = renderHook(() => useToolRisk());
    await waitFor(() => expect(result.current.known).toBe(true));
    expect(result.current.isReversible('search')).toBe(true);
  });

  it('treats a tool that stops for approval as not freely reversible', async () => {
    const { result } = renderHook(() => useToolRisk());
    await waitFor(() => expect(result.current.known).toBe(true));
    expect(result.current.isReversible('send_email')).toBe(false);
  });

  it('treats a tool the policy refuses as not freely reversible', async () => {
    const { result } = renderHook(() => useToolRisk());
    await waitFor(() => expect(result.current.known).toBe(true));
    expect(result.current.isReversible('delete_everything')).toBe(false);
  });

  it('assumes the kinder case for a tool it has never heard of', async () => {
    const { result } = renderHook(() => useToolRisk());
    await waitFor(() => expect(result.current.known).toBe(true));
    expect(result.current.isReversible('something_new')).toBe(true);
  });

  it('assumes the kinder case before the policy has loaded', () => {
    const { result } = renderHook(() => useToolRisk());
    expect(result.current.isReversible('send_email')).toBe(true);
  });

  it('says it does not know when the policy is out of reach', async () => {
    answer.ok = false;
    const { result } = renderHook(() => useToolRisk());
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(result.current.known).toBe(false);
  });

  it('assumes the kinder case when the policy is out of reach', async () => {
    answer.ok = false;
    const { result } = renderHook(() => useToolRisk());
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(result.current.isReversible('send_email')).toBe(true);
  });

  it('survives a policy that is not shaped as expected', async () => {
    answer.body = { approval: 'nope' };
    const { result } = renderHook(() => useToolRisk());
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(result.current.isReversible('send_email')).toBe(true);
  });
});
