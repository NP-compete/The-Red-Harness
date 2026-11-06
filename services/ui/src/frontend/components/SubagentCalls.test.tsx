import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { SubagentCalls } from './SubagentCalls';

const api = vi.hoisted(() => ({ getSubagentCalls: vi.fn() }));
vi.mock('../services/subagent-calls', () => api);

beforeEach(() => {
  vi.clearAllMocks();
  api.getSubagentCalls.mockResolvedValue([
    { name: 'dataverse_execute_sql', args: { sql: 'SELECT 1' } },
    { name: 'read_file', args: { path: '/notes.md' } },
  ]);
});

describe('SubagentCalls', () => {
  it('says how many steps the delegated work took', async () => {
    render(<SubagentCalls threadId="t1" />);
    expect(await screen.findByText(/2 steps/)).toBeInTheDocument();
  });

  it('counts a single step in the singular', async () => {
    api.getSubagentCalls.mockResolvedValue([{ name: 'read_file', args: {} }]);
    render(<SubagentCalls threadId="t1" />);
    expect(await screen.findByText(/1 step\b/)).toBeInTheDocument();
  });

  it('keeps the detail closed until it is asked for', async () => {
    render(<SubagentCalls threadId="t1" />);
    await screen.findByText(/2 steps/);
    expect(screen.queryByText('dataverse_execute_sql')).not.toBeInTheDocument();
  });

  it('names each tool once opened', async () => {
    render(<SubagentCalls threadId="t1" />);
    await userEvent.click(await screen.findByRole('button'));
    expect(screen.getByText('dataverse_execute_sql')).toBeInTheDocument();
    expect(screen.getByText('read_file')).toBeInTheDocument();
  });

  it('shows what each tool was given', async () => {
    render(<SubagentCalls threadId="t1" />);
    await userEvent.click(await screen.findByRole('button'));
    expect(screen.getByText(/SELECT 1/)).toBeInTheDocument();
  });

  it('stays out of the way when there is nothing to show', async () => {
    api.getSubagentCalls.mockResolvedValue([]);
    const { container } = render(<SubagentCalls threadId="t1" />);
    await vi.waitFor(() => expect(api.getSubagentCalls).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it('asks nothing when there is no conversation yet', () => {
    render(<SubagentCalls threadId="" />);
    expect(api.getSubagentCalls).not.toHaveBeenCalled();
  });
});
