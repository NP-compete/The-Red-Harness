import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { WorkspaceFiles } from './WorkspaceFiles';

const api = vi.hoisted(() => ({
  listWorkspaceFiles: vi.fn(),
  readWorkspaceFile: vi.fn(),
  deleteWorkspaceFile: vi.fn(),
}));
vi.mock('../../services/workspace-files', () => api);

beforeEach(() => {
  vi.clearAllMocks();
  api.listWorkspaceFiles.mockResolvedValue([
    { path: '/notes.md', bytes: 6, modified: '2026-10-27 17:38:29+00:00' },
  ]);
  api.readWorkspaceFile.mockResolvedValue('Hello.');
  api.deleteWorkspaceFile.mockResolvedValue(true);
});

describe('WorkspaceFiles', () => {
  it('names a file the agent wrote', async () => {
    render(<WorkspaceFiles />);
    expect(await screen.findByText('/notes.md')).toBeInTheDocument();
  });

  it('says how big it is', async () => {
    render(<WorkspaceFiles />);
    expect(await screen.findByText(/6 bytes/)).toBeInTheDocument();
  });

  it('counts a larger file in kilobytes', async () => {
    api.listWorkspaceFiles.mockResolvedValue([
      { path: '/report.md', bytes: 4000, modified: '' },
    ]);
    render(<WorkspaceFiles />);
    expect(await screen.findByText(/4\.0 kB/)).toBeInTheDocument();
  });

  it('says so when the agent has written nothing', async () => {
    api.listWorkspaceFiles.mockResolvedValue([]);
    render(<WorkspaceFiles />);
    expect(await screen.findByText(/has not written any files/i)).toBeInTheDocument();
  });

  it('says nothing before the answer is in', () => {
    const { container } = render(<WorkspaceFiles />);
    expect(container).toBeEmptyDOMElement();
  });

  it('keeps the contents out of the way until asked for', async () => {
    render(<WorkspaceFiles />);
    await screen.findByText('/notes.md');
    expect(screen.queryByText('Hello.')).not.toBeInTheDocument();
  });

  it('shows what a file says when it is opened', async () => {
    render(<WorkspaceFiles />);
    await userEvent.click(await screen.findByRole('button', { name: /^\/notes\.md/ }));
    expect(await screen.findByText('Hello.')).toBeInTheDocument();
  });

  it('says so when the file has gone since the list was made', async () => {
    api.readWorkspaceFile.mockResolvedValue(null);
    render(<WorkspaceFiles />);
    await userEvent.click(await screen.findByRole('button', { name: /^\/notes\.md/ }));
    expect(await screen.findByText(/could not be read/i)).toBeInTheDocument();
  });

  it('does not remove a file on the first press', async () => {
    render(<WorkspaceFiles />);
    await userEvent.click(await screen.findByRole('button', { name: /delete \/notes\.md/i }));
    expect(api.deleteWorkspaceFile).not.toHaveBeenCalled();
  });

  it('asks before removing anything', async () => {
    render(<WorkspaceFiles />);
    await userEvent.click(await screen.findByRole('button', { name: /delete \/notes\.md/i }));
    expect(await screen.findByRole('button', { name: /really/i })).toBeInTheDocument();
  });

  it('removes it on the second press', async () => {
    render(<WorkspaceFiles />);
    await userEvent.click(await screen.findByRole('button', { name: /delete \/notes\.md/i }));
    await userEvent.click(await screen.findByRole('button', { name: /really/i }));
    expect(api.deleteWorkspaceFile).toHaveBeenCalledWith('/notes.md');
  });

  it('takes the file out of the list once it is gone', async () => {
    render(<WorkspaceFiles />);
    await userEvent.click(await screen.findByRole('button', { name: /delete \/notes\.md/i }));
    await userEvent.click(await screen.findByRole('button', { name: /really/i }));
    expect(await screen.findByText(/has not written any files/i)).toBeInTheDocument();
  });

  it('leaves the file in place when it could not be removed', async () => {
    api.deleteWorkspaceFile.mockResolvedValue(false);
    render(<WorkspaceFiles />);
    await userEvent.click(await screen.findByRole('button', { name: /delete \/notes\.md/i }));
    await userEvent.click(await screen.findByRole('button', { name: /really/i }));
    expect(await screen.findByText('/notes.md')).toBeInTheDocument();
  });
});
