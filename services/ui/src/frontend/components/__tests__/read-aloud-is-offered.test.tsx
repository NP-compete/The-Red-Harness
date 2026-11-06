import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

/**
 * Hearing an answer instead of reading it.
 *
 * The button, the hook behind it and the words for it all
 * exist. Nothing rendered any of them, so the capability was
 * present in the codebase and absent from the product — which
 * is the worst of both: it looks supported to anybody reading
 * the source and does not exist for anybody using it.
 *
 * It belongs on the agent's own answers, beside copy and
 * feedback. Not on what somebody typed: they know what they
 * wrote.
 */

const transcript = () =>
  readFileSync(join(__dirname, '..', 'ChatMessagesView.tsx'), 'utf-8');

describe('an answer can be read aloud', () => {
  it('the control is in the transcript', () => {
    expect(transcript()).toContain('ReadAloudButton');
  });

  it('it sits with the other things you can do to an answer', () => {
    // Next to copy and feedback, not somewhere of its own:
    // a control for an answer belongs with the answer's
    // controls.
    const source = transcript();
    // The row, not one side of it: where it sits relative to
    // copy or feedback is a layout choice, and pinning that
    // would make a reorder look like a regression.
    const row = source.slice(
      source.indexOf('<MessageCopyButton'),
      source.indexOf('aiGeneratedContent'),
    );
    expect(row).toContain('ReadAloudButton');
  });

  it('it is given the answer, not the markup', () => {
    // Reading raw markdown aloud announces asterisks and
    // backticks.
    const source = transcript();
    const at = source.indexOf('<ReadAloudButton');
    expect(source.slice(at, at + 120)).toMatch(/text=\{(plain|copyText)\}/);
  });
});

describe('the button itself', () => {
  it('says nothing when the browser cannot speak', async () => {
    // Rendering a control that does nothing is worse than
    // leaving it out; the hook reports whether speech exists.
    const source = readFileSync(join(__dirname, '..', 'ReadAloudButton.tsx'), 'utf-8');
    expect(source).toContain('if (!available) return null;');
  });
});
