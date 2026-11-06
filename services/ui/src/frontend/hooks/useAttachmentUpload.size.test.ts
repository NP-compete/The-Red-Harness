import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAttachmentUpload } from './useAttachmentUpload';

const api = vi.hoisted(() => ({ uploadAttachments: vi.fn() }));
vi.mock('../services/attachments-api', () => api);

const status = vi.hoisted(() => ({ getExtractionStatus: vi.fn() }));
vi.mock('../services/extraction-status', () => status);

function file(name: string, bytes: number): File {
  return new File([new Uint8Array(bytes)], name, { type: 'text/plain' });
}

beforeEach(() => {
  vi.clearAllMocks();
  api.uploadAttachments.mockResolvedValue({ attachments: [], summary: '' });
  status.getExtractionStatus.mockResolvedValue({
    engine: 'builtin',
    reachable: true,
    detail: '',
    fallback: true,
    handles: [],
    maxBytes: 100,
  });
});

describe('useAttachmentUpload — files that are too big', () => {
  it('sends a file within the limit', async () => {
    const { result } = renderHook(() => useAttachmentUpload({ threadId: 't1' }));
    await act(async () => { await result.current.upload([file('small.txt', 50)]); });
    expect(api.uploadAttachments).toHaveBeenCalled();
  });

  it('does not send one over the limit', async () => {
    const { result } = renderHook(() => useAttachmentUpload({ threadId: 't1' }));
    await act(async () => { await result.current.upload([file('big.txt', 500)]); });
    expect(api.uploadAttachments).not.toHaveBeenCalled();
  });

  it('says which file was too big and what the limit is', async () => {
    const onError = vi.fn();
    const { result } = renderHook(() => useAttachmentUpload({ threadId: 't1', onError }));
    await act(async () => { await result.current.upload([file('big.txt', 500)]); });
    expect(onError).toHaveBeenCalledWith(expect.stringContaining('big.txt'));
  });

  it('still sends the files that do fit', async () => {
    const { result } = renderHook(() => useAttachmentUpload({ threadId: 't1' }));
    await act(async () => {
      await result.current.upload([file('big.txt', 500), file('small.txt', 10)]);
    });
    const sent = api.uploadAttachments.mock.calls[0][1] as File[];
    expect(sent.map((f) => f.name)).toEqual(['small.txt']);
  });

  it('sends everything when the agent will not say what the limit is', async () => {
    status.getExtractionStatus.mockResolvedValue(null);
    const { result } = renderHook(() => useAttachmentUpload({ threadId: 't1' }));
    await act(async () => { await result.current.upload([file('big.txt', 5_000_000)]); });
    expect(api.uploadAttachments).toHaveBeenCalled();
  });

  it('sends everything when the agent reports no limit', async () => {
    status.getExtractionStatus.mockResolvedValue({
      engine: 'builtin', reachable: true, detail: '', fallback: true, handles: [], maxBytes: 0,
    });
    const { result } = renderHook(() => useAttachmentUpload({ threadId: 't1' }));
    await act(async () => { await result.current.upload([file('big.txt', 5_000_000)]); });
    expect(api.uploadAttachments).toHaveBeenCalled();
  });
});
