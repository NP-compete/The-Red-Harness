import { afterEach, describe, expect, it, vi } from 'vitest';

import { getSubagentCalls } from './subagent-calls';

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

describe('getSubagentCalls', () => {
  it('lists what the delegated steps ran', async () => {
    answers(200, {
      thread_id: 't1',
      tool_calls: [{ tool_name: 'dataverse_execute_sql', arguments: { sql: 'SELECT 1' } }],
    });
    expect(await getSubagentCalls('t1')).toEqual([
      { name: 'dataverse_execute_sql', args: { sql: 'SELECT 1' } },
    ]);
  });

  it('returns nothing when the reader may not see them', async () => {
    answers(403, {});
    expect(await getSubagentCalls('t1')).toEqual([]);
  });

  it('returns nothing when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await getSubagentCalls('t1')).toEqual([]);
  });

  it('skips an entry with no tool named', async () => {
    answers(200, { tool_calls: [{ arguments: {} }, { tool_name: 'read', arguments: {} }] });
    expect(await getSubagentCalls('t1')).toEqual([{ name: 'read', args: {} }]);
  });

  it('copes with an answer carrying no calls at all', async () => {
    answers(200, { thread_id: 't1' });
    expect(await getSubagentCalls('t1')).toEqual([]);
  });
});
