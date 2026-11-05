import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => vi.restoreAllMocks());

import { assistantRows } from '@/lib/assistant-rows';

/**
 * Rows for the per-assistant table.
 *
 * The figures arrive from the agent; what happens here is the
 * part that misleads if it is careless — a rate with no
 * denominator, a measurement nobody took shown as zero, and an
 * identifier presented as though it were a name.
 */
const ROW = {
  assistant: 'fe096781-5601-53d2-b2f6-0d3403f7e9ca',
  runs: 254,
  errors: 24,
  threads: 214,
  p95_seconds: 289.23,
};

describe('assistantRows', () => {
  it('keeps every assistant', () => {
    expect(assistantRows([ROW, { ...ROW, assistant: 'b' }])).toHaveLength(2);
  });

  it('busiest first, because that is the one being asked about', () => {
    const rows = assistantRows([
      { ...ROW, assistant: 'quiet', runs: 2 },
      { ...ROW, assistant: 'busy', runs: 99 },
    ]);
    expect(rows[0].assistant).toBe('busy');
  });

  describe('the error rate', () => {
    it('is a share of the runs', () => {
      expect(assistantRows([{ ...ROW, runs: 100, errors: 25 }])[0].errorRate).toBe(0.25);
    });

    it('is absent when nothing ran', () => {
      // Not zero. No runs means no rate, and zero per cent is a
      // claim that everything worked.
      expect(assistantRows([{ ...ROW, runs: 0, errors: 0 }])[0].errorRate).toBeNull();
    });
  });

  describe('a latency nobody measured', () => {
    it('stays absent rather than becoming zero', () => {
      expect(assistantRows([{ ...ROW, p95_seconds: null }])[0].p95).toBeNull();
    });

    it('a real measurement survives', () => {
      expect(assistantRows([ROW])[0].p95).toBe(289.23);
    });
  });

  describe('the name', () => {
    it('is shortened, because an identifier is not a name', () => {
      // A full uuid in a table column pushes every real figure
      // off the right-hand edge.
      expect(assistantRows([ROW])[0].label.length).toBeLessThan(
        ROW.assistant.length,
      );
    });

    it('keeps enough to tell two apart', () => {
      const rows = assistantRows([
        { ...ROW, assistant: 'fe096781-aaaa' },
        { ...ROW, assistant: 'fe096781-bbbb' },
      ]);
      expect(rows[0].label).not.toBe(rows[1].label);
    });

    it('leaves a readable name alone', () => {
      expect(assistantRows([{ ...ROW, assistant: 'curator' }])[0].label).toBe('curator');
    });

    it('carries the full identifier for anyone who needs it', () => {
      expect(assistantRows([ROW])[0].assistant).toBe(ROW.assistant);
    });
  });
});

describe('fetchAssistants', () => {
  it('reads the rows the agent sends', async () => {
    const { fetchAssistants } = await import('@/services/analytics-api');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ assistants: [{ ...ROW }] }),
    } as unknown as Response);
    expect(await fetchAssistants(7)).toHaveLength(1);
  });

  it('asks for the window it was given', async () => {
    const { fetchAssistants } = await import('@/services/analytics-api');
    const fetched = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ assistants: [] }),
    } as unknown as Response);
    await fetchAssistants(30);
    expect(String(fetched.mock.calls[0][0])).toContain('days=30');
  });

  it('keeps a missing latency missing rather than making it zero', async () => {
    const { fetchAssistants } = await import('@/services/analytics-api');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ assistants: [{ ...ROW, p95_seconds: null }] }),
    } as unknown as Response);
    expect((await fetchAssistants(7))[0].p95_seconds).toBeNull();
  });
});
