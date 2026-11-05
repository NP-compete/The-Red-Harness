import { afterEach, describe, expect, it, vi } from 'vitest';

import { deadRunReason, runStillGoing } from './run-status';

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

const run = (over: Record<string, unknown> = {}) => ({
  run_id: 'r1',
  status: 'error',
  error_message: 'Max retries exceeded after repeated worker failures',
  created_at: '2026-10-27T17:21:51.012823Z',
  ...over,
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('deadRunReason', () => {
  it('says why a run cannot be carried on with', async () => {
    answers(200, [run()]);
    expect(await deadRunReason('t1')).toBe(
      'Max retries exceeded after repeated worker failures',
    );
  });

  it('says nothing about a run that is still going', async () => {
    answers(200, [run({ status: 'running', error_message: null })]);
    expect(await deadRunReason('t1')).toBeNull();
  });

  it('says nothing about a run that finished', async () => {
    answers(200, [run({ status: 'success', error_message: null })]);
    expect(await deadRunReason('t1')).toBeNull();
  });

  it('says nothing about a run that is waiting on a person', async () => {
    answers(200, [run({ status: 'interrupted', error_message: null })]);
    expect(await deadRunReason('t1')).toBeNull();
  });

  it('judges by the newest run, not the oldest', async () => {
    answers(200, [
      run({ created_at: '2026-10-27T10:00:00Z' }),
      run({ status: 'interrupted', error_message: null, created_at: '2026-10-27T18:00:00Z' }),
    ]);
    expect(await deadRunReason('t1')).toBeNull();
  });

  it('has something to say even when the agent gave no reason', async () => {
    answers(200, [run({ error_message: null })]);
    expect(await deadRunReason('t1')).toMatch(/stopped/i);
  });

  it('says nothing when the thread has no runs', async () => {
    answers(200, []);
    expect(await deadRunReason('t1')).toBeNull();
  });

  it('says nothing when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await deadRunReason('t1')).toBeNull();
  });
});

describe('runStillGoing', () => {
  it('says a running run is still going', async () => {
    answers(200, [run({ status: 'running', error_message: null })]);
    expect(await runStillGoing('t1')).toBe(true);
  });

  it('says a finished run is not', async () => {
    answers(200, [run({ status: 'success', error_message: null })]);
    expect(await runStillGoing('t1')).toBe(false);
  });

  it('says a cancelled run is not', async () => {
    answers(200, [run({ status: 'interrupted', error_message: null })]);
    expect(await runStillGoing('t1')).toBe(false);
  });

  it('judges by the newest run', async () => {
    answers(200, [
      run({ status: 'running', error_message: null, created_at: '2026-10-27T10:00:00Z' }),
      run({ status: 'success', error_message: null, created_at: '2026-10-27T18:00:00Z' }),
    ]);
    expect(await runStillGoing('t1')).toBe(false);
  });

  it('does not claim anything about a thread with no runs', async () => {
    answers(200, []);
    expect(await runStillGoing('t1')).toBe(false);
  });

  it('does not claim anything when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await runStillGoing('t1')).toBe(false);
  });
});
