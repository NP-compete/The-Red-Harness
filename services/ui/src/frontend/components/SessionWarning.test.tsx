import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SessionWarning } from './SessionWarning';

const NOW = new Date('2026-03-01T12:00:00Z');

function inMinutes(n: number) {
  return new Date(NOW.getTime() + n * 60_000);
}

describe('SessionWarning', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(NOW);
  });
  afterEach(() => vi.useRealTimers());

  it('says nothing while the session has plenty left', () => {
    const { container } = render(<SessionWarning expiresAt={inMinutes(120)} hasDraft={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('speaks up as the session nears its end', () => {
    render(<SessionWarning expiresAt={inMinutes(4)} hasDraft={false} />);
    expect(screen.getByText('You will be signed out in 4 minutes')).toBeInTheDocument();
  });

  it('counts a final minute properly', () => {
    render(<SessionWarning expiresAt={inMinutes(1)} hasDraft={false} />);
    expect(screen.getByText('You will be signed out in 1 minute')).toBeInTheDocument();
  });

  it('warns louder when there is unsent work', () => {
    render(<SessionWarning expiresAt={inMinutes(3)} hasDraft />);
    expect(
      screen.getByText('You have unsaved work in this conversation'),
    ).toBeInTheDocument();
  });

  it('says nothing of unsaved work when the box is empty', () => {
    render(<SessionWarning expiresAt={inMinutes(3)} hasDraft={false} />);
    expect(screen.queryByText(/unsaved work/)).not.toBeInTheDocument();
  });

  it('says plainly once the session has gone', () => {
    render(<SessionWarning expiresAt={inMinutes(-1)} hasDraft={false} />);
    expect(screen.getByText('You have been signed out')).toBeInTheDocument();
  });

  it('cannot be waved away once signed out', () => {
    render(<SessionWarning expiresAt={inMinutes(-1)} hasDraft={false} />);
    expect(screen.queryByRole('button', { name: /close/i })).not.toBeInTheDocument();
  });

  it('says nothing when nobody told it when the session ends', () => {
    const { container } = render(<SessionWarning expiresAt={undefined} hasDraft={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});
