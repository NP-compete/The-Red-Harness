import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { SystemHealth } from './SystemHealth';

const api = vi.hoisted(() => ({ getSystemHealth: vi.fn() }));
vi.mock('../../services/system-health', () => api);

beforeEach(() => {
  vi.clearAllMocks();
  api.getSystemHealth.mockResolvedValue([
    { name: 'database', state: 'connected' },
    { name: 'langgraph store', state: 'connected' },
  ]);
});

describe('SystemHealth', () => {
  it('names each part the agent depends on', async () => {
    render(<SystemHealth />);
    expect(await screen.findByText('database')).toBeInTheDocument();
    expect(screen.getByText('langgraph store')).toBeInTheDocument();
  });

  it('sums up what is working', async () => {
    render(<SystemHealth />);
    expect(await screen.findByText(/2 connected/)).toBeInTheDocument();
  });

  it('puts what is failing first', async () => {
    api.getSystemHealth.mockResolvedValue([
      { name: 'database', state: 'connected' },
      { name: 'redis', state: 'degraded' },
    ]);
    render(<SystemHealth />);
    await screen.findByText('redis');
    const names = screen.getAllByRole('listitem').map((n) => n.textContent);
    expect(names[0]).toContain('redis');
  });

  it('says a failing part is unavailable', async () => {
    api.getSystemHealth.mockResolvedValue([{ name: 'redis', state: 'degraded' }]);
    render(<SystemHealth />);
    expect(await screen.findByText('Unavailable')).toBeInTheDocument();
  });

  it('says nothing before the answer is in', () => {
    const { container } = render(<SystemHealth />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says nothing when the agent cannot be asked', async () => {
    api.getSystemHealth.mockResolvedValue(null);
    const { container } = render(<SystemHealth />);
    await vi.waitFor(() => expect(api.getSystemHealth).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});
