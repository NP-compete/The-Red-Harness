import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { StoppingNotice } from '../StoppingNotice';

/**
 * The gap between asking the agent to stop and it stopping.
 *
 * The stream ends the instant stop is pressed, so the screen
 * goes quiet and looks finished — while the step already in
 * flight runs to completion and does whatever it was going to
 * do. Somebody who pressed stop to prevent exactly that has
 * been told, by the silence, that they succeeded.
 *
 * The transcript takes a `stopping` prop and did nothing with
 * it; the notice that says this was mounted nowhere.
 */

describe('the notice', () => {
  it('says the step in flight still finishes', () => {
    render(<StoppingNotice stopping />);
    expect(screen.getByText(/already in flight/i)).toBeTruthy();
  });

  it('is announced, because it appears after the screen went quiet', () => {
    render(<StoppingNotice stopping />);
    expect(screen.getByRole('status')).toBeTruthy();
  });

  it('is absent when nothing is stopping', () => {
    const { container } = render(<StoppingNotice stopping={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('the transcript shows it', () => {
  it('does something with the prop it is given', () => {
    // It was destructured and then ignored, which type-checks
    // and renders nothing.
    const text = readFileSync(join(__dirname, '..', 'ChatMessagesView.tsx'), 'utf-8');
    expect(text).toContain('StoppingNotice');
    expect(text).toMatch(/stopping=\{stopping\}|<StoppingNotice\s+stopping/);
  });
});
