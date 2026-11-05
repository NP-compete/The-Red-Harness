import { describe, expect, it } from 'vitest';

import { sumUsage } from './thread-usage';

const answer = (input: number, output: number, cacheRead = 0) => ({
  type: 'ai',
  usage_metadata: {
    input_tokens: input,
    output_tokens: output,
    total_tokens: input + output,
    input_token_details: { cache_read: cacheRead },
  },
});

describe('sumUsage', () => {
  it('adds up what every answer in the thread used', () => {
    expect(sumUsage([answer(100, 20), answer(300, 50)])).toMatchObject({
      inputTokens: 400,
      outputTokens: 70,
      used: 470,
    });
  });

  it('ignores messages that carry no count', () => {
    expect(sumUsage([{ type: 'human', content: 'hi' }, answer(10, 5)])).toMatchObject({
      used: 15,
    });
  });

  it('reports how much of the input was read from cache', () => {
    expect(sumUsage([answer(100, 10, 80), answer(100, 10, 20)])?.cacheRead).toBe(100);
  });

  it('has nothing to say about a thread with no counts', () => {
    expect(sumUsage([{ type: 'human', content: 'hi' }])).toBeNull();
  });

  it('has nothing to say about an empty thread', () => {
    expect(sumUsage([])).toBeNull();
  });

  it('falls back to the total when the split is missing', () => {
    expect(sumUsage([{ type: 'ai', usage_metadata: { total_tokens: 90 } }])).toMatchObject({
      used: 90,
      inputTokens: 0,
      outputTokens: 0,
    });
  });

  it('adds the parts when no total was given', () => {
    expect(
      sumUsage([{ type: 'ai', usage_metadata: { input_tokens: 7, output_tokens: 3 } }]),
    ).toMatchObject({ used: 10 });
  });
});
