import { describe, expect, it } from 'vitest';

import { compactionSummary } from './compaction-marker';

const OPENING = 'Here is a summary of the conversation to date:';

describe('compactionSummary', () => {
  it('recognises the stand-in left where earlier turns were', () => {
    const found = compactionSummary({
      type: 'human',
      content: `${OPENING}\n\nThey asked about the onboarding fee.`,
    });
    expect(found).toBe('They asked about the onboarding fee.');
  });

  it('leaves something the person actually said alone', () => {
    expect(compactionSummary({ type: 'human', content: 'What is the fee?' })).toBeNull();
  });

  it('does not mistake an answer that talks about summaries', () => {
    expect(
      compactionSummary({ type: 'ai', content: `${OPENING}\n\nSomething.` }),
    ).toBeNull();
  });

  it('is not thrown by the wording being indented or spaced differently', () => {
    const found = compactionSummary({
      type: 'human',
      content: `  ${OPENING}   \n\n  They asked about the fee.  `,
    });
    expect(found).toBe('They asked about the fee.');
  });

  it('reads a message whose content came in parts', () => {
    const found = compactionSummary({
      type: 'human',
      content: [{ type: 'text', text: `${OPENING}\n\nThey asked about the fee.` }],
    });
    expect(found).toBe('They asked about the fee.');
  });

  it('still marks a summary that has no body', () => {
    expect(compactionSummary({ type: 'human', content: OPENING })).toBe('');
  });

  it('says nothing about a message with no content', () => {
    expect(compactionSummary({ type: 'human', content: '' })).toBeNull();
  });

  it('says nothing about something that is not a message', () => {
    expect(compactionSummary(null)).toBeNull();
    expect(compactionSummary(undefined)).toBeNull();
  });

  it('does not match a message that merely quotes the wording later on', () => {
    expect(
      compactionSummary({ type: 'human', content: `Please write: ${OPENING}` }),
    ).toBeNull();
  });
});
