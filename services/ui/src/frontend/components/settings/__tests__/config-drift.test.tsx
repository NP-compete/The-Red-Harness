import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ConfigDrift } from '../ConfigDrift';
import * as api from '../../../services/config-editing-api';

/**
 * What this deployment has changed about itself, and how to stop.
 *
 * Editing configuration here means a change to the same path in
 * the pipeline stops arriving. That cost is invisible from
 * either side — the repository says one thing, the agent does
 * another, and each looks correct on its own — so the only
 * place it can be seen is a screen that says so.
 *
 * Which makes the empty state the important one. "Nothing has
 * drifted" and "I could not ask" must not look alike: the first
 * is reassurance and the second is a question nobody answered.
 *
 * The export stays offered in a read-only deployment, because
 * exporting is how a drifted deployment gets back. Read-only
 * means it cannot be edited, not that it is no longer drifted.
 */

afterEach(() => vi.restoreAllMocks());

const PROMPT = 'config/agent/PROMPT.md';

const drifted = () =>
  vi.spyOn(api, 'readConfigDrift').mockResolvedValue([
    {
      path: PROMPT,
      baseline: 'the original wording',
      overlay: 'the edited wording',
      author: 'ada',
      at: '2026-10-29T10:00:00Z',
    },
  ]);

const mode = (editable: boolean) =>
  vi.spyOn(api, 'readEditingState').mockResolvedValue({
    mode: editable ? 'readwrite' : 'readonly',
    editable,
    paths: [PROMPT],
  });

describe('when something has drifted', () => {
  it('names the path', async () => {
    drifted();
    mode(true);
    render(<ConfigDrift />);
    expect(await screen.findByText(PROMPT)).toBeTruthy();
  });

  it('shows what the pipeline says and what this deployment says', async () => {
    drifted();
    mode(true);
    render(<ConfigDrift />);
    expect(await screen.findByText(/the original wording/)).toBeTruthy();
    expect(await screen.findByText(/the edited wording/)).toBeTruthy();
  });

  it('says who changed it', async () => {
    drifted();
    mode(true);
    render(<ConfigDrift />);
    expect(await screen.findByText(/ada/)).toBeTruthy();
  });

  it('warns that the pipeline no longer reaches these files', async () => {
    drifted();
    mode(true);
    render(<ConfigDrift />);
    expect(await screen.findByText(/no longer reach/i)).toBeTruthy();
  });
});

describe('going back', () => {
  it('offers to adopt the pipeline version', async () => {
    drifted();
    mode(true);
    render(<ConfigDrift />);
    expect(await screen.findByRole('button', { name: /use the pipeline version/i })).toBeTruthy();
  });

  it('asks the agent when pressed', async () => {
    drifted();
    mode(true);
    const adopted = vi.spyOn(api, 'adoptBaseline').mockResolvedValue({ ok: true });
    render(<ConfigDrift />);
    await userEvent.click(await screen.findByRole('button', { name: /use the pipeline version/i }));
    await waitFor(() => expect(adopted).toHaveBeenCalledWith(PROMPT));
  });

  it('shows the agent its own words when it refuses', async () => {
    drifted();
    mode(true);
    vi.spyOn(api, 'adoptBaseline').mockResolvedValue({
      ok: false,
      detail: 'no store is chosen to keep the change in',
    });
    render(<ConfigDrift />);
    await userEvent.click(await screen.findByRole('button', { name: /use the pipeline version/i }));
    expect(await screen.findByText(/no store is chosen/)).toBeTruthy();
  });
});

describe('the history of a drifted path', () => {
  it('is shown beside it', async () => {
    // Somebody asking "why is it like this" is already looking
    // at the row. Making them go elsewhere for the answer is
    // the kind of split that leaves the second screen unvisited.
    drifted();
    mode(true);
    vi.spyOn(api, 'readConfigHistory').mockResolvedValue([
      { version: 1, author: 'ada', at: '2026-10-28T09:00:00Z', content: 'first' },
    ]);
    render(<ConfigDrift />);
    expect(await screen.findByText(/nothing is erased/i)).toBeTruthy();
  });
});

describe('a read-only deployment', () => {
  it('is not offered a way to change anything', async () => {
    drifted();
    mode(false);
    render(<ConfigDrift />);
    await screen.findByText(PROMPT);
    expect(screen.queryByRole('button', { name: /use the pipeline version/i })).toBeNull();
  });

  it('can still see what has drifted', async () => {
    // Read-only means it cannot be edited, not that it is no
    // longer drifted. Hiding this would hide the problem at
    // the moment somebody is resolving it.
    drifted();
    mode(false);
    render(<ConfigDrift />);
    expect(await screen.findByText(PROMPT)).toBeTruthy();
  });

  it('can still take the export', async () => {
    drifted();
    mode(false);
    render(<ConfigDrift />);
    expect(await screen.findByRole('link', { name: /export|download/i })).toBeTruthy();
  });
});

describe('when nothing has drifted', () => {
  it('says so plainly', async () => {
    vi.spyOn(api, 'readConfigDrift').mockResolvedValue([]);
    mode(true);
    render(<ConfigDrift />);
    expect(await screen.findByText(/matches|nothing/i)).toBeTruthy();
  });

  it('does not warn about a pipeline that is not being bypassed', async () => {
    vi.spyOn(api, 'readConfigDrift').mockResolvedValue([]);
    mode(true);
    render(<ConfigDrift />);
    await screen.findByText(/matches|nothing/i);
    expect(screen.queryByText(/no longer reach/i)).toBeNull();
  });
});

describe('when the agent could not be asked', () => {
  it('shows nothing rather than claiming nothing has drifted', async () => {
    // The distinction this whole screen rests on. Reassurance
    // nobody earned is worse than silence.
    vi.spyOn(api, 'readConfigDrift').mockResolvedValue(null);
    mode(true);
    const { container } = render(<ConfigDrift />);
    await waitFor(() => expect(container.textContent).not.toContain('matches'));
  });
});
