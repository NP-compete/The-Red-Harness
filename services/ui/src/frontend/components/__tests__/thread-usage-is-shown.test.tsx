import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

/**
 * What this conversation has cost, where somebody can see it.
 *
 * The component, the endpoint it reads and the words for it
 * all existed and nothing rendered them. Spend that is only
 * visible on a settings page is spend nobody looks at until
 * the bill — and the agent charges per token, so a long
 * conversation is the expensive one and the only place anybody
 * is looking is the conversation.
 *
 * Beside the response timing, which is already shown on the
 * last answer and answers the neighbouring question: what did
 * that cost, in time and in tokens.
 */

const transcript = () =>
  readFileSync(join(__dirname, '..', 'ChatMessagesView.tsx'), 'utf-8');

describe('the conversation says what it used', () => {
  it('the line is in the transcript', () => {
    expect(transcript()).toContain('ThreadTokenUsageLine');
  });

  it('it is given the thread, since the total is per conversation', () => {
    const source = transcript();
    const at = source.indexOf('<ThreadTokenUsageLine');
    expect(source.slice(at, at + 200)).toMatch(/threadId=\{/);
  });

  it('it is given the turns on screen', () => {
    // A deployment that keeps no running total still has one
    // for the turns in front of you, because every answer
    // carries its own count.
    const source = transcript();
    const at = source.indexOf('<ThreadTokenUsageLine');
    expect(source.slice(at, at + 200)).toMatch(/messages=\{/);
  });

  it('it appears once, on the last answer', () => {
    // Once per conversation, not once per turn: it is a
    // running total, and repeating it after every answer
    // reads as a per-answer figure.
    const source = transcript();
    expect(source.match(/<ThreadTokenUsageLine/g)).toHaveLength(1);
    const at = source.indexOf('<ThreadTokenUsageLine');
    const before = source.slice(0, at);
    expect(before.lastIndexOf('showResponseTiming')).toBeGreaterThan(
      before.lastIndexOf('messages.map'),
    );
  });
});
