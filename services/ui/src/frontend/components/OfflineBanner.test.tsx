import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { OfflineBanner } from './OfflineBanner';

const connection = vi.hoisted(() => ({
  current: { connected: true, secondsDown: 0, warn: false },
}));

vi.mock('../hooks/useConnectionState', () => ({
  useConnectionState: () => connection.current,
}));

function offlineFor(secondsDown: number) {
  connection.current = { connected: false, secondsDown, warn: secondsDown >= 10 };
}

describe('OfflineBanner', () => {
  it('shows nothing while connected', () => {
    connection.current = { connected: true, secondsDown: 0, warn: false };
    const { container } = render(<OfflineBanner />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows nothing during a blip', () => {
    offlineFor(2);
    const { container } = render(<OfflineBanner />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says plainly when the connection has gone', () => {
    offlineFor(30);
    render(<OfflineBanner />);
    expect(screen.getByText('No connection')).toBeInTheDocument();
  });

  it('says what is waiting to go out', () => {
    offlineFor(30);
    render(<OfflineBanner queued={2} />);
    expect(screen.getByText('2 messages will send when you are back')).toBeInTheDocument();
  });

  it('warns that a run in flight may have finished without us', () => {
    offlineFor(30);
    render(<OfflineBanner runInFlight />);
    expect(
      screen.getByText('A run was in progress — its outcome is unknown until you reconnect'),
    ).toBeInTheDocument();
  });

  it('offers a way to try again', () => {
    offlineFor(30);
    render(<OfflineBanner />);
    expect(screen.getByRole('button', { name: 'Retry now' })).toBeInTheDocument();
  });

  it('announces itself to a screen reader', () => {
    offlineFor(30);
    render(<OfflineBanner />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
