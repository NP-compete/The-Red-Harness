import { describe, expect, it } from 'vitest';

import { countEffort } from './thread-effort';

const said = (content: string) => ({ type: 'ai', content });
const called = (...names: string[]) => ({
  type: 'ai',
  content: '',
  tool_calls: names.map((name, i) => ({ name, args: {}, id: `c${i}` })),
});

describe('countEffort', () => {
  it('counts every time the model was asked', () => {
    expect(countEffort([said('hello'), called('search'), said('done')])?.modelCalls).toBe(3);
  });

  it('counts the tools those turns used', () => {
    expect(countEffort([called('search', 'read'), called('search')])?.toolCalls).toBe(3);
  });

  it('ignores what the person typed', () => {
    expect(countEffort([{ type: 'human', content: 'hi' }, said('hello')])?.modelCalls).toBe(1);
  });

  it('has nothing to report on a conversation with no answers', () => {
    expect(countEffort([{ type: 'human', content: 'hi' }])).toBeNull();
  });

  it('has nothing to report on an empty conversation', () => {
    expect(countEffort([])).toBeNull();
  });

  it('reports no tools when none were used', () => {
    expect(countEffort([said('hello')])?.toolCalls).toBe(0);
  });
});
