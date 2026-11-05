import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { CompactionNote } from '../CompactionNote';

/**
 * Where a conversation was shortened, and what was kept.
 *
 * A divider saying "earlier turns were summarised" tells
 * somebody that something is missing and nothing about what.
 * The summary is what the agent is still working from, so it
 * is the one thing worth being able to read — otherwise a
 * compaction is indistinguishable from the agent having
 * forgotten, which is the complaint this marker exists to
 * answer.
 *
 * The transcript rendered its own divider and threw the
 * summary away, while the component that can show it was
 * mounted nowhere.
 */

describe('the marker', () => {
  it('says the conversation was shortened', () => {
    render(<CompactionNote summary="They asked about pricing." />);
    expect(screen.getByText(/summarised/i)).toBeTruthy();
  });

  it('keeps what was kept out of the way until asked', () => {
    render(<CompactionNote summary="They asked about pricing." />);
    expect(screen.queryByText('They asked about pricing.')).toBeNull();
  });

  it('shows it when asked', async () => {
    render(<CompactionNote summary="They asked about pricing." />);
    await userEvent.click(screen.getByRole('button'));
    expect(screen.getByText('They asked about pricing.')).toBeTruthy();
  });

  it('says whether it is open, for somebody not looking at it', async () => {
    render(<CompactionNote summary="They asked about pricing." />);
    const toggle = screen.getByRole('button');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
  });

  it('offers nothing to open when nothing was kept', () => {
    // A compaction with no summary is still worth marking —
    // the turns are gone either way — but there is nothing to
    // read, and a control that opens onto nothing is worse
    // than no control.
    render(<CompactionNote summary="" />);
    expect(screen.getByText(/summarised/i)).toBeTruthy();
    expect(screen.queryByRole('button')).toBeNull();
  });
});

describe('the transcript uses it', () => {
  it('does not draw its own divider instead', () => {
    // The inline version showed where compaction happened and
    // discarded the summary, so there was nothing to expand.
    const text = readFileSync(join(__dirname, '..', 'ChatMessagesView.tsx'), 'utf-8');
    expect(text).toContain('CompactionNote');
    expect(text).not.toContain("{t('chat.compacted')}");
  });
});
