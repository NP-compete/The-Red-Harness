import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  adoptBaseline,
  readConfigDrift,
  readEditingState,
} from './config-editing-api';

/**
 * Talking to the agent about its own configuration.
 *
 * The rule that shapes all of this: a deployment that has not
 * been opened for editing has no write routes at all, so the
 * browser gets a 404 rather than a refusal. That is not an
 * error to report — it is the ordinary answer, and showing a
 * failure for it would tell somebody something is broken when
 * the deployment is behaving exactly as configured.
 */

afterEach(() => vi.restoreAllMocks());

const answers = (status: number, body: unknown = {}) =>
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as never);

describe('asking whether this deployment may be edited', () => {
  it('reports the mode', async () => {
    answers(200, { mode: 'readwrite', editable: true, paths: ['a'] });
    expect((await readEditingState())?.editable).toBe(true);
  });

  it('reports read-only as read-only rather than as a failure', async () => {
    answers(200, { mode: 'readonly', editable: false, paths: ['a'] });
    const found = await readEditingState();
    expect(found?.mode).toBe('readonly');
    expect(found?.editable).toBe(false);
  });

  it('gives nothing when the agent cannot be reached', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('offline'));
    expect(await readEditingState()).toBeNull();
  });

  it('gives nothing rather than guessing when the agent errors', async () => {
    // Guessing "editable" here would offer controls that fail;
    // guessing "read-only" would hide a feature that works.
    answers(500);
    expect(await readEditingState()).toBeNull();
  });
});

describe('reading what has drifted', () => {
  it('comes back as rows', async () => {
    answers(200, {
      paths: [{ path: 'config/agent/PROMPT.md', baseline: 'a', overlay: 'b' }],
    });
    expect(await readConfigDrift()).toHaveLength(1);
  });

  it('nothing drifted is an empty list, not nothing', async () => {
    // Null would make "no drift" indistinguishable from "could
    // not ask", and those read very differently on screen.
    answers(200, { paths: [] });
    expect(await readConfigDrift()).toEqual([]);
  });

  it('an unreachable agent is nothing, not an empty list', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('offline'));
    expect(await readConfigDrift()).toBeNull();
  });
});

describe('adopting the baseline for one path', () => {
  it('says so when it worked', async () => {
    answers(200, { path: 'config/agent/PROMPT.md', version: 2 });
    expect((await adoptBaseline('config/agent/PROMPT.md')).ok).toBe(true);
  });

  it('a read-only deployment answers that there is no such route', async () => {
    // 404 here is the deployment being what it was configured
    // to be. It is reported as a refusal with a reason, never
    // as a fault.
    answers(404);
    const found = await adoptBaseline('config/agent/PROMPT.md');
    expect(found.ok).toBe(false);
    expect(found.detail?.toLowerCase()).toContain('read-only');
  });

  it('a refusal with a reason keeps the reason', async () => {
    answers(501, { detail: 'no store is chosen to keep the change in' });
    const found = await adoptBaseline('config/agent/PROMPT.md');
    expect(found.ok).toBe(false);
    expect(found.detail).toContain('no store');
  });

  it('an unreachable agent is a refusal, not a silent success', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('offline'));
    expect((await adoptBaseline('x')).ok).toBe(false);
  });
});
