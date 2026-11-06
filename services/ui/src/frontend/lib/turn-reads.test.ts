import { describe, expect, it } from 'vitest';

import { readsForAnswer } from './turn-reads';

const messages = [
  { type: 'human', content: 'q1' },
  { type: 'ai', content: '', tool_calls: [{ id: 'c1', name: 'search' }] },
  { type: 'tool', tool_call_id: 'c1', content: 'first result' },
  { type: 'ai', content: 'answer one' },
  { type: 'human', content: 'q2' },
  { type: 'ai', content: '', tool_calls: [{ id: 'c2', name: 'fetch' }] },
  { type: 'tool', tool_call_id: 'c2', content: 'second result' },
  { type: 'ai', content: 'answer two' },
] as never[];

describe('readsForAnswer', () => {
  it('carries the shape the agent worked out', () => {
    const described = [
      { type: 'human', content: 'q' },
      {
        type: 'ai',
        content: '',
        tool_calls: [
          { id: 'c1', name: 'people', content: '[]', shape: { kind: 'table', rows: 2, columns: ['name'], needs_paging: false, needs_collapsing: false, language: '' } },
        ],
      },
      { type: 'ai', content: 'an answer' },
    ] as never[];
    expect(readsForAnswer(described, 2)[0].shape).toEqual({
      kind: 'table',
      rows: 2,
      columns: ['name'],
      language: '',
      needsPaging: false,
      needsCollapsing: false,
    });
  });

  it('leaves the shape off when the agent did not describe it', () => {
    const plain = [
      { type: 'human', content: 'q' },
      { type: 'ai', content: '', tool_calls: [{ id: 'c1', name: 'x', content: 'hello' }] },
      { type: 'ai', content: 'an answer' },
    ] as never[];
    expect(readsForAnswer(plain, 2)[0].shape).toBeUndefined();
  });

  it('takes only what this turn read', () => {
    expect(readsForAnswer(messages, 7)).toEqual([{ source: 'fetch', text: 'second result' }]);
  });

  it('does not reach back into an earlier turn', () => {
    expect(readsForAnswer(messages, 3)).toEqual([{ source: 'search', text: 'first result' }]);
  });

  it('names the tool that returned each result', () => {
    expect(readsForAnswer(messages, 7)[0].source).toBe('fetch');
  });

  it('is empty for an answer that read nothing', () => {
    const plain = [
      { type: 'human', content: 'q' },
      { type: 'ai', content: 'an answer' },
    ] as never[];
    expect(readsForAnswer(plain, 1)).toEqual([]);
  });

  it('reads a result folded into the call that asked for it', () => {
    // How the thread arrives from the agent: the tool message is merged
    // into the tool call rather than left beside it.
    const merged = [
      { type: 'human', content: 'q' },
      {
        type: 'ai',
        content: '',
        tool_calls: [{ id: 'c1', name: 'handbook_search', content: 'the limit is 500' }],
      },
      { type: 'ai', content: 'an answer' },
    ] as never[];
    expect(readsForAnswer(merged, 2)).toEqual([
      { source: 'handbook_search', text: 'the limit is 500' },
    ]);
  });

  it('ignores a call still waiting for its result', () => {
    const pending = [
      { type: 'human', content: 'q' },
      { type: 'ai', content: '', tool_calls: [{ id: 'c1', name: 'search' }] },
      { type: 'ai', content: 'an answer' },
    ] as never[];
    expect(readsForAnswer(pending, 2)).toEqual([]);
  });

  it('falls back to the call id when the tool has no name', () => {
    const odd = [
      { type: 'human', content: 'q' },
      { type: 'tool', tool_call_id: 'c9', content: 'something' },
      { type: 'ai', content: 'an answer' },
    ] as never[];
    expect(readsForAnswer(odd, 2)[0].source).toBe('c9');
  });
});
