import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ThreadTags } from './ThreadTags';

const api = vi.hoisted(() => ({
  getThreadTags: vi.fn(),
  setThreadTags: vi.fn(),
  listTags: vi.fn(),
}));
vi.mock('../services/tags-api', () => api);

beforeEach(() => {
  // Call history survives between tests otherwise, so a later
  // "was not called" assertion sees an earlier test's calls.
  vi.clearAllMocks();
  api.getThreadTags.mockResolvedValue(['billing']);
  api.setThreadTags.mockImplementation((_id: string, tags: string[]) =>
    Promise.resolve([...tags].map((t) => t.trim().toLowerCase()).sort()),
  );
  api.listTags.mockResolvedValue([{ tag: 'billing', threads: 4 }, { tag: 'travel', threads: 1 }]);
});

describe('ThreadTags', () => {
  it('shows the tags already on the conversation', async () => {
    render(<ThreadTags threadId="t1" />);
    expect(await screen.findByText('billing')).toBeInTheDocument();
  });

  it('offers a way to add one', async () => {
    render(<ThreadTags threadId="t1" />);
    expect(await screen.findByRole('button', { name: /add tag/i })).toBeInTheDocument();
  });

  it('saves a new tag alongside the existing ones', async () => {
    render(<ThreadTags threadId="t1" />);
    await userEvent.click(await screen.findByRole('button', { name: /add tag/i }));
    await userEvent.type(screen.getByRole('textbox'), 'travel{Enter}');
    expect(api.setThreadTags).toHaveBeenCalledWith('t1', ['billing', 'travel']);
  });

  it('shows the tag as the agent stored it, not as it was typed', async () => {
    render(<ThreadTags threadId="t1" />);
    await userEvent.click(await screen.findByRole('button', { name: /add tag/i }));
    await userEvent.type(screen.getByRole('textbox'), '  Travel  {Enter}');
    expect(await screen.findByText('travel')).toBeInTheDocument();
  });

  it('removes a tag when asked', async () => {
    render(<ThreadTags threadId="t1" />);
    await userEvent.click(await screen.findByRole('button', { name: /remove billing/i }));
    expect(api.setThreadTags).toHaveBeenCalledWith('t1', []);
  });

  it('ignores an empty tag rather than asking the agent to refuse it', async () => {
    render(<ThreadTags threadId="t1" />);
    await userEvent.click(await screen.findByRole('button', { name: /add tag/i }));
    await userEvent.type(screen.getByRole('textbox'), '   {Enter}');
    expect(api.setThreadTags).not.toHaveBeenCalled();
  });

  it('does not add a tag the conversation already has', async () => {
    render(<ThreadTags threadId="t1" />);
    await userEvent.click(await screen.findByRole('button', { name: /add tag/i }));
    await userEvent.type(screen.getByRole('textbox'), 'billing{Enter}');
    expect(api.setThreadTags).not.toHaveBeenCalled();
  });

  it('keeps the tags it had when the agent refuses a change', async () => {
    api.setThreadTags.mockResolvedValue(null);
    render(<ThreadTags threadId="t1" />);
    await userEvent.click(await screen.findByRole('button', { name: /remove billing/i }));
    await waitFor(() => expect(screen.getByText('billing')).toBeInTheDocument());
  });

  it('suggests tags already in use elsewhere', async () => {
    render(<ThreadTags threadId="t1" />);
    await userEvent.click(await screen.findByRole('button', { name: /add tag/i }));
    expect(await screen.findByRole('option', { name: /travel/ })).toBeInTheDocument();
  });

  it('does not suggest a tag this conversation already has', async () => {
    render(<ThreadTags threadId="t1" />);
    await userEvent.click(await screen.findByRole('button', { name: /add tag/i }));
    await screen.findByRole('option', { name: /travel/ });
    expect(screen.queryByRole('option', { name: /billing/ })).not.toBeInTheDocument();
  });
});
