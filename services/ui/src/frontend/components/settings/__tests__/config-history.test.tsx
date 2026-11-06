import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ConfigHistory } from '../ConfigHistory';
import * as api from '../../../services/config-editing-api';

/**
 * What this file used to say, and who changed it.
 *
 * The question behind this screen is almost always "why is it
 * like this", asked by somebody who did not do it. So the
 * useful answer is a name and a time against each version, and
 * the ability to put one back without having to retype it.
 *
 * Restoring adds a version rather than removing the ones after
 * it, and the screen says so before anybody presses anything —
 * otherwise "restore" reads as "delete what I did since", and
 * somebody hesitates over the one action that is safe.
 */

afterEach(() => vi.restoreAllMocks());

const PROMPT = 'config/agent/PROMPT.md';

const history = (versions: unknown[]) =>
  vi.spyOn(api, 'readConfigHistory').mockResolvedValue(versions as never);

const two = () => [
  { version: 1, author: 'ada', at: '2026-10-28T09:00:00Z', content: 'first' },
  { version: 2, author: 'bo', at: '2026-10-29T09:00:00Z', content: 'second' },
];

const mode = (editable: boolean) =>
  vi.spyOn(api, 'readEditingState').mockResolvedValue({
    mode: editable ? 'readwrite' : 'readonly',
    editable,
    paths: [PROMPT],
  });

describe('a path with a history', () => {
  it('lists every version', async () => {
    history(two());
    mode(true);
    render(<ConfigHistory path={PROMPT} />);
    await waitFor(() => expect(screen.getAllByRole('listitem')).toHaveLength(2));
  });

  it('names who made each one', async () => {
    history(two());
    mode(true);
    render(<ConfigHistory path={PROMPT} />);
    expect(await screen.findByText(/ada/)).toBeTruthy();
    expect(await screen.findByText(/bo/)).toBeTruthy();
  });

  it('shows the newest first', async () => {
    history(two());
    mode(true);
    render(<ConfigHistory path={PROMPT} />);
    const rows = await screen.findAllByRole('listitem');
    expect(rows[0].textContent).toContain('bo');
  });

  it('says which one is in force', async () => {
    history(two());
    mode(true);
    render(<ConfigHistory path={PROMPT} />);
    expect(await screen.findByText(/in force|current/i)).toBeTruthy();
  });
});

describe('putting a version back', () => {
  it('says restoring does not erase anything, before anything is pressed', async () => {
    // Otherwise "restore" reads as "delete what I did since",
    // and somebody hesitates over the one safe action.
    history(two());
    mode(true);
    render(<ConfigHistory path={PROMPT} />);
    expect(await screen.findByText(/nothing is erased/i)).toBeTruthy();
  });

  it('offers to restore an older version', async () => {
    history(two());
    mode(true);
    render(<ConfigHistory path={PROMPT} />);
    expect(await screen.findByRole('button', { name: /restore/i })).toBeTruthy();
  });

  it('does not offer to restore the one already in force', async () => {
    history(two());
    mode(true);
    render(<ConfigHistory path={PROMPT} />);
    await screen.findByRole('button', { name: /restore/i });
    expect(screen.getAllByRole('button', { name: /restore/i })).toHaveLength(1);
  });

  it('asks the agent for the right version', async () => {
    history(two());
    mode(true);
    const reverted = vi.spyOn(api, 'revertConfig').mockResolvedValue({ ok: true });
    render(<ConfigHistory path={PROMPT} />);
    await userEvent.click(await screen.findByRole('button', { name: /restore/i }));
    await waitFor(() => expect(reverted).toHaveBeenCalledWith(PROMPT, 1));
  });

  it('shows the agent its own words when it refuses', async () => {
    history(two());
    mode(true);
    vi.spyOn(api, 'revertConfig').mockResolvedValue({
      ok: false,
      detail: 'no store is chosen to keep the change in',
    });
    render(<ConfigHistory path={PROMPT} />);
    await userEvent.click(await screen.findByRole('button', { name: /restore/i }));
    expect(await screen.findByText(/no store is chosen/)).toBeTruthy();
  });
});

describe('a read-only deployment', () => {
  it('can read the history', async () => {
    history(two());
    mode(false);
    render(<ConfigHistory path={PROMPT} />);
    expect(await screen.findByText(/ada/)).toBeTruthy();
  });

  it('is offered no way to restore', async () => {
    history(two());
    mode(false);
    render(<ConfigHistory path={PROMPT} />);
    await screen.findByText(/ada/);
    expect(screen.queryByRole('button', { name: /restore/i })).toBeNull();
  });
});

describe('a path with no history', () => {
  it('says so rather than showing an empty list', async () => {
    history([]);
    mode(true);
    render(<ConfigHistory path={PROMPT} />);
    expect(await screen.findByText(/no changes recorded/i)).toBeTruthy();
  });
});

describe('when the agent could not be asked', () => {
  it('does not claim there were no changes', async () => {
    vi.spyOn(api, 'readConfigHistory').mockResolvedValue(null);
    mode(true);
    const { container } = render(<ConfigHistory path={PROMPT} />);
    await waitFor(() =>
      expect(container.textContent?.toLowerCase()).not.toContain('no changes'),
    );
  });
});
