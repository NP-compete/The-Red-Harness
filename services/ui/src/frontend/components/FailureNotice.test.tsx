import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { FailureNotice } from './FailureNotice';

function appData(data: Record<string, unknown> | undefined) {
  (window as unknown as { APP_DATA?: unknown }).APP_DATA = data;
}

afterEach(() => appData(undefined));

describe('FailureNotice', () => {
  it('says nothing when the run did not fail', () => {
    const { container } = render(<FailureNotice error={null} onRetry={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says something a reader can understand', () => {
    render(<FailureNotice error={'ECONNRESET at line 42'} onRetry={vi.fn()} />);
    expect(screen.getByText('The agent encountered an error:')).toBeInTheDocument();
  });

  it('shows what the agent actually said', () => {
    // The only account the reader gets of what went wrong.
    appData({ userRole: 'users' });
    render(<FailureNotice error={'Model configuration is invalid'} onRetry={vi.fn()} />);
    expect(screen.getByText('Model configuration is invalid')).toBeInTheDocument();
  });

  it('offers to try again', async () => {
    const onRetry = vi.fn();
    render(<FailureNotice error={'boom'} onRetry={onRetry} />);
    await userEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(onRetry).toHaveBeenCalled();
  });

  it('announces itself to a screen reader', () => {
    render(<FailureNotice error={'boom'} onRetry={vi.fn()} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
