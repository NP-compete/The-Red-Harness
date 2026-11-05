import { afterEach, describe, expect, it, vi } from 'vitest';

import { dictationOffered, transcribeDictation } from './speech-api';

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

const recording = () => new Blob([new Uint8Array([1, 2, 3])], { type: 'audio/webm' });

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('dictationOffered', () => {
  it('says yes when the deployment has turned it on', async () => {
    answers(200, { dictation: true });
    expect(await dictationOffered()).toBe(true);
  });

  it('says no when it has not', async () => {
    answers(200, { dictation: false });
    expect(await dictationOffered()).toBe(false);
  });

  it('says no rather than guessing when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await dictationOffered()).toBe(false);
  });

  it('says no when the agent has no such endpoint', async () => {
    answers(404, {});
    expect(await dictationOffered()).toBe(false);
  });
});

describe('transcribeDictation', () => {
  it('hands back what was said', async () => {
    answers(200, { text: 'book the room' });
    expect(await transcribeDictation(recording())).toEqual({ text: 'book the room' });
  });

  it('treats silence as nothing said, not as a failure', async () => {
    answers(200, { text: '' });
    expect(await transcribeDictation(recording())).toEqual({ text: '' });
  });

  it('passes on the reason a recording could not be used', async () => {
    answers(422, { detail: 'That recording is too long to dictate.' });
    expect(await transcribeDictation(recording())).toEqual({
      text: '',
      problem: 'That recording is too long to dictate.',
    });
  });

  it('has something to say when the agent gave no reason', async () => {
    answers(500, {});
    const found = await transcribeDictation(recording());
    expect(found.problem).toBeTruthy();
  });

  it('has something to say when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect((await transcribeDictation(recording())).problem).toBeTruthy();
  });

  it('sends the recording as a file rather than as a blob of text', async () => {
    answers(200, { text: 'ok' });
    await transcribeDictation(recording());
    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(init.body).toBeInstanceOf(FormData);
  });
});
