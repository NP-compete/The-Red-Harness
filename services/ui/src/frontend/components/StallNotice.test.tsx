import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { StallNotice } from './StallNotice';

const quiet = vi.hoisted(() => ({ seconds: 0 }));

vi.mock('../hooks/useQuietFor', () => ({
  useQuietFor: () => quiet.seconds,
}));

describe('StallNotice', () => {
  it('says nothing while nothing is running', () => {
    quiet.seconds = 120;
    const { container } = render(<StallNotice isLoading={false} signature="a" onStop={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says nothing while output is still arriving', () => {
    quiet.seconds = 3;
    const { container } = render(<StallNotice isLoading signature="a" onStop={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('speaks up once a run has gone quiet', () => {
    quiet.seconds = 45;
    render(<StallNotice isLoading signature="a" onStop={vi.fn()} />);
    expect(screen.getByText('Nothing has happened for 45 seconds')).toBeInTheDocument();
  });

  it('counts a long silence in minutes', () => {
    quiet.seconds = 120;
    render(<StallNotice isLoading signature="a" onStop={vi.fn()} />);
    expect(screen.getByText('Nothing has happened for 2 minutes')).toBeInTheDocument();
  });

  it('names the tool when one is running', () => {
    quiet.seconds = 45;
    render(<StallNotice isLoading signature="a" toolRunning="search" onStop={vi.fn()} />);
    expect(screen.getByText('search is taking longer than expected')).toBeInTheDocument();
  });

  it('promises a running tool will finish before the run stops', () => {
    quiet.seconds = 45;
    render(<StallNotice isLoading signature="a" toolRunning="search" onStop={vi.fn()} />);
    expect(screen.getByText('search will finish before the run stops')).toBeInTheDocument();
  });

  it('offers a way to stop', () => {
    quiet.seconds = 45;
    render(<StallNotice isLoading signature="a" onStop={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Stop this run' })).toBeInTheDocument();
  });

  it('stops the run when asked', async () => {
    quiet.seconds = 45;
    const onStop = vi.fn();
    render(<StallNotice isLoading signature="a" onStop={onStop} />);
    await userEvent.click(screen.getByRole('button', { name: 'Stop this run' }));
    expect(onStop).toHaveBeenCalled();
  });

  it('says nothing while a person is being waited on', () => {
    quiet.seconds = 120;
    const { container } = render(
      <StallNotice isLoading signature="a" awaitingPerson onStop={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('announces itself to a screen reader', () => {
    quiet.seconds = 45;
    render(<StallNotice isLoading signature="a" onStop={vi.fn()} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
