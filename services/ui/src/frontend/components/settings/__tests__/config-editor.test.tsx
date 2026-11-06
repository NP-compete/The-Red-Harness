import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ConfigEditor } from '../ConfigEditor';
import * as api from '../../../services/config-editing-api';

/**
 * Changing a configuration file from the browser.
 *
 * The thing that makes this safe to offer is that the agent
 * refuses a change that would not be valid, and says which
 * file and which field. So the editor's job is mostly to get
 * out of the way and then report that refusal faithfully: a
 * generic "could not save" would send somebody reading their
 * own diff for a problem the agent has already located.
 *
 * It shows the *effective* text — what the agent reads now,
 * edits included. Showing the mounted file instead would hand
 * somebody the version they are not running, and their save
 * would quietly discard whatever had been edited since.
 *
 * A read-only deployment is offered no editor at all, rather
 * than an editor whose save fails.
 */

afterEach(() => vi.restoreAllMocks());

const PROMPT = 'config/agent/PROMPT.md';

const mode = (editable: boolean, paths: string[] = [PROMPT]) =>
  vi.spyOn(api, 'readEditingState').mockResolvedValue({
    mode: editable ? 'readwrite' : 'readonly',
    editable,
    paths,
  });

const file = (content: string, version = 0) =>
  vi
    .spyOn(api, 'readConfigFile')
    .mockResolvedValue({ path: PROMPT, content, exists: true, version });

describe('choosing what to edit', () => {
  it('offers the paths the deployment says are editable', async () => {
    mode(true, [PROMPT, 'config/agent/runtime/agent.yaml']);
    file('the prompt');
    render(<ConfigEditor />);
    const chooser = await screen.findByRole('combobox');
    expect(chooser.textContent).toContain(PROMPT);
    expect(chooser.textContent).toContain('agent.yaml');
  });

  it('shows what that file currently says', async () => {
    mode(true);
    file('the current wording');
    render(<ConfigEditor />);
    expect(await screen.findByDisplayValue('the current wording')).toBeTruthy();
  });
});

describe('saving', () => {
  it('sends what was typed', async () => {
    mode(true);
    file('old');
    const saved = vi
      .spyOn(api, 'saveConfigFile')
      .mockResolvedValue({ ok: true });

    render(<ConfigEditor />);
    const box = await screen.findByDisplayValue('old');
    await userEvent.clear(box);
    await userEvent.type(box, 'new');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));

    // The third argument is the version this editor loaded. Sending
    // it is what makes a concurrent save a 409 rather than a silent
    // overwrite (MU-5).
    await waitFor(() => expect(saved).toHaveBeenCalledWith(PROMPT, 'new', 0));
  });

  it('hands back the version it loaded, so a stale save is refused', async () => {
    mode(true);
    file('old', 7);
    const saved = vi.spyOn(api, 'saveConfigFile').mockResolvedValue({ ok: true });

    render(<ConfigEditor />);
    const box = await screen.findByDisplayValue('old');
    await userEvent.type(box, '!');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => expect(saved).toHaveBeenCalledWith(PROMPT, 'old!', 7));
  });

  it('says so when it worked', async () => {
    mode(true);
    file('old');
    vi.spyOn(api, 'saveConfigFile').mockResolvedValue({ ok: true });
    render(<ConfigEditor />);
    await screen.findByDisplayValue('old');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(await screen.findByText(/saved/i)).toBeTruthy();
  });

  it('warns that the change will not survive a restart', async () => {
    // The store is in the process. Somebody who changes the
    // prompt, sees it work and finds it gone a day later has
    // no way to connect the two unless they were told.
    mode(true);
    file('old');
    vi.spyOn(api, 'saveConfigFile').mockResolvedValue({ ok: true, durable: false });
    render(<ConfigEditor />);
    await screen.findByDisplayValue('old');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(await screen.findByText(/restart/i)).toBeTruthy();
  });
});

describe('when the agent refuses', () => {
  it('shows which file and field, in the agent own words', async () => {
    // A generic "could not save" sends somebody reading their
    // own diff for a problem already located for them.
    mode(true);
    file('old');
    vi.spyOn(api, 'saveConfigFile').mockResolvedValue({
      ok: false,
      detail: 'runtime/agent.yaml:model.name: must be a string',
    });
    render(<ConfigEditor />);
    await screen.findByDisplayValue('old');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(await screen.findByText(/model\.name/)).toBeTruthy();
  });

  it('keeps what was typed so it is not lost', async () => {
    mode(true);
    file('old');
    vi.spyOn(api, 'saveConfigFile').mockResolvedValue({
      ok: false,
      detail: 'not valid',
    });
    render(<ConfigEditor />);
    const box = await screen.findByDisplayValue('old');
    await userEvent.clear(box);
    await userEvent.type(box, 'my careful edit');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    await screen.findByText(/not valid/);
    expect((box as HTMLTextAreaElement).value).toBe('my careful edit');
  });
});

describe('a read-only deployment', () => {
  it('is offered no editor at all', async () => {
    // Rather than an editor whose save always fails.
    mode(false);
    file('the prompt');
    const { container } = render(<ConfigEditor />);
    await waitFor(() => expect(container.querySelector('textarea')).toBeNull());
  });

  it('says why there is nothing to edit', async () => {
    mode(false);
    file('the prompt');
    render(<ConfigEditor />);
    expect(await screen.findByText(/read-only/i)).toBeTruthy();
  });
});

describe('when the agent could not be asked', () => {
  it('shows no editor rather than one that cannot save', async () => {
    vi.spyOn(api, 'readEditingState').mockResolvedValue(null);
    file('x');
    const { container } = render(<ConfigEditor />);
    await waitFor(() => expect(container.querySelector('textarea')).toBeNull());
  });
});

describe('where edits go', () => {
  it('warns before anybody types when the store is not durable', async () => {
    mode(true);
    file('old');
    vi.spyOn(api, 'readEditingState').mockResolvedValue({
      mode: 'readwrite',
      editable: true,
      paths: [PROMPT],
      store: 'memory',
      durable: false,
    });

    render(<ConfigEditor />);
    // Before the textarea has been touched: "saved, but this will
    // not survive a restart" is the right sentence at the wrong
    // moment once the work is already done.
    expect(await screen.findByText(/lost when it restarts/)).toBeInTheDocument();
  });

  it('says nothing when edits are durable', async () => {
    mode(true);
    file('old');
    vi.spyOn(api, 'readEditingState').mockResolvedValue({
      mode: 'readwrite',
      editable: true,
      paths: [PROMPT],
      store: 'postgres',
      durable: true,
    });

    render(<ConfigEditor />);
    await screen.findByDisplayValue('old');
    expect(screen.queryByText(/lost when it restarts/)).toBeNull();
  });
});
