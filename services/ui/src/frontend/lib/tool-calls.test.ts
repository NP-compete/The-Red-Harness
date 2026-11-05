import { describe, expect, it } from 'vitest';

import { markWrites, recordToolCall, runningTool } from './tool-calls';

const T0 = 1_700_000_000_000;

describe('recordToolCall', () => {
  it('records a tool the moment it is called', () => {
    const after = recordToolCall([], { type: 'ai', tool_calls: [{ id: 'c1', name: 'search' }] }, T0);
    expect(after).toEqual([
      { id: 'c1', tool: 'search', state: 'running', startedAt: T0, ms: 0, writes: false },
    ]);
  });

  it('records each tool in a parallel call', () => {
    const after = recordToolCall(
      [],
      { type: 'ai', tool_calls: [{ id: 'c1', name: 'search' }, { id: 'c2', name: 'fetch' }] },
      T0,
    );
    expect(after.map((e) => e.tool)).toEqual(['search', 'fetch']);
  });

  it('marks a tool finished when its result arrives', () => {
    const running = recordToolCall([], { type: 'ai', tool_calls: [{ id: 'c1', name: 'search' }] }, T0);
    const done = recordToolCall(running, { type: 'tool', tool_call_id: 'c1' }, T0 + 2000);
    expect(done[0].state).toBe('done');
  });

  it('measures how long the call took', () => {
    const running = recordToolCall([], { type: 'ai', tool_calls: [{ id: 'c1', name: 'search' }] }, T0);
    const done = recordToolCall(running, { type: 'tool', tool_call_id: 'c1' }, T0 + 2000);
    expect(done[0].ms).toBe(2000);
  });

  it('keeps the time the call began', () => {
    const running = recordToolCall([], { type: 'ai', tool_calls: [{ id: 'c1', name: 'search' }] }, T0);
    const done = recordToolCall(running, { type: 'tool', tool_call_id: 'c1' }, T0 + 2000);
    expect(done[0].startedAt).toBe(T0);
  });

  it('leaves a call still running unmeasured', () => {
    // Half a duration reads as a finished step that was very fast.
    const running = recordToolCall([], { type: 'ai', tool_calls: [{ id: 'c1', name: 'search' }] }, T0);
    expect(running[0].ms).toBe(0);
  });

  it('marks a call the policy stops for as one that changes things', () => {
    const after = recordToolCall(
      [],
      { type: 'ai', tool_calls: [{ id: 'c1', name: 'send_email' }] },
      T0,
      (tool) => tool === 'send_email',
    );
    expect(after[0].writes).toBe(true);
  });

  it('does not record the same call twice', () => {
    const once = recordToolCall([], { type: 'ai', tool_calls: [{ id: 'c1', name: 'search' }] }, T0);
    const again = recordToolCall(once, { type: 'ai', tool_calls: [{ id: 'c1', name: 'search' }] }, T0 + 50);
    expect(again).toHaveLength(1);
  });

  it('ignores an ordinary answer', () => {
    expect(recordToolCall([], { type: 'ai', content: 'hello' }, T0)).toEqual([]);
  });

  it('ignores a question', () => {
    expect(recordToolCall([], { type: 'human', content: 'hello' }, T0)).toEqual([]);
  });

  it('ignores a result for a call it never saw', () => {
    expect(recordToolCall([], { type: 'tool', tool_call_id: 'c9' }, T0)).toEqual([]);
  });

  it('leaves the previous list untouched', () => {
    const before = recordToolCall([], { type: 'ai', tool_calls: [{ id: 'c1', name: 'search' }] }, T0);
    recordToolCall(before, { type: 'tool', tool_call_id: 'c1' }, T0 + 1);
    expect(before[0].state).toBe('running');
  });

  it('falls back to the call id when a tool is unnamed', () => {
    const after = recordToolCall([], { type: 'ai', tool_calls: [{ id: 'c1' }] }, T0);
    expect(after[0].tool).toBe('c1');
  });
});

describe('markWrites', () => {
  const calls = [
    { id: 'c1', tool: 'search', state: 'done' as const, startedAt: 0, ms: 10, writes: false },
    { id: 'c2', tool: 'send_email', state: 'done' as const, startedAt: 0, ms: 10, writes: false },
  ];

  it('marks a tool the policy stops for', () => {
    const marked = markWrites(calls, (tool) => tool !== 'send_email');
    expect(marked[1].writes).toBe(true);
  });

  it('leaves a tool the policy waves through alone', () => {
    const marked = markWrites(calls, (tool) => tool !== 'send_email');
    expect(marked[0].writes).toBe(false);
  });

  it('marks nothing when every tool is reversible', () => {
    // Which is also what an unread policy reports, so an unknown
    // policy never claims a call changed something.
    const marked = markWrites(calls, () => true);
    expect(marked.every((call) => !call.writes)).toBe(true);
  });

  it('leaves the recorded calls untouched', () => {
    markWrites(calls, () => false);
    expect(calls[1].writes).toBe(false);
  });
});

describe('runningTool', () => {
  const call = (id: string, tool: string, state: string) => ({
    id,
    tool,
    state,
    startedAt: 0,
    ms: 0,
    writes: false,
  });

  it('names the call still in flight', () => {
    expect(runningTool([call('1', 'search', 'done'), call('2', 'curator', 'running')] as never))
      .toBe('curator');
  });

  it('names the most recent one when several are in flight', () => {
    expect(runningTool([call('1', 'search', 'running'), call('2', 'curator', 'running')] as never))
      .toBe('curator');
  });

  it('names nothing once every call has come back', () => {
    expect(runningTool([call('1', 'search', 'done')] as never)).toBe('');
  });

  it('names nothing when no tool has been called', () => {
    expect(runningTool([])).toBe('');
  });
});
