import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ChannelsSection } from './ChannelsSection';

const api = vi.hoisted(() => ({ listChannels: vi.fn() }));
vi.mock('../../services/channels-api', () => api);

beforeEach(() => {
  vi.clearAllMocks();
  api.listChannels.mockResolvedValue([
    { name: 'support', type: 'slack', assistantId: 'a1' },
    { name: 'alerts', type: 'webhook' },
  ]);
});

describe('ChannelsSection', () => {
  it('names each channel the agent is reachable on', async () => {
    render(<ChannelsSection />);
    expect(await screen.findByText('support')).toBeInTheDocument();
    expect(screen.getByText('alerts')).toBeInTheDocument();
  });

  it('says what kind of channel each is', async () => {
    render(<ChannelsSection />);
    expect(await screen.findByText('slack')).toBeInTheDocument();
  });

  it('says plainly when the agent is reachable nowhere else', async () => {
    api.listChannels.mockResolvedValue([]);
    render(<ChannelsSection />);
    expect(await screen.findByText(/no channels are configured/i)).toBeInTheDocument();
  });

  it('shows nothing at all until it has asked', () => {
    const { container } = render(<ChannelsSection />);
    expect(container).toBeEmptyDOMElement();
  });
});
