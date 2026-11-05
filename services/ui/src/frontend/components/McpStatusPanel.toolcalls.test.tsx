import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { McpStatusPanel } from './McpStatusPanel';

const calls = [
  { id: 'c1', tool: 'handbook_search', state: 'done' as const, startedAt: 0, ms: 400, writes: false },
  { id: 'c2', tool: 'send_email', state: 'done' as const, startedAt: 0, ms: 2500, writes: true },
];

describe('McpStatusPanel with recorded tool calls', () => {
  it('shows nothing when the run called no tools', () => {
    const { container } = render(<McpStatusPanel mcpEvents={[]} toolCalls={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('opens even without the status channel the agent never sends', async () => {
    render(<McpStatusPanel mcpEvents={[]} toolCalls={calls} />);
    await userEvent.click(screen.getByText(/tool activity/i));
    expect(screen.getByText('handbook_search')).toBeInTheDocument();
  });

  it('says how long a call took', async () => {
    render(<McpStatusPanel mcpEvents={[]} toolCalls={calls} />);
    await userEvent.click(screen.getByText(/tool activity/i));
    expect(screen.getByText('2.5s')).toBeInTheDocument();
  });

  it('names the slowest call once it is worth mentioning', async () => {
    render(<McpStatusPanel mcpEvents={[]} toolCalls={calls} />);
    await userEvent.click(screen.getByText(/tool activity/i));
    expect(screen.getByText('send_email took 2.5s')).toBeInTheDocument();
  });

  it('marks a call that changed something', async () => {
    render(<McpStatusPanel mcpEvents={[]} toolCalls={calls} />);
    await userEvent.click(screen.getByText(/tool activity/i));
    expect(screen.getByText(/1 changed something/i)).toBeInTheDocument();
  });

  it('sums up where it looked, before the detail', async () => {
    render(<McpStatusPanel mcpEvents={[]} toolCalls={calls} />);
    await userEvent.click(screen.getByText(/tool activity/i));
    // Only the reading tools: a write is not somewhere it looked.
    expect(screen.getByText('Looked in handbook_search')).toBeInTheDocument();
  });
});
