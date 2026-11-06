import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { CompactionNote } from './CompactionNote';

describe('CompactionNote', () => {
  it('says the earlier turns were summarised', () => {
    render(<CompactionNote summary="They asked about the fee." />);
    expect(screen.getByText(/summarised|summarized/i)).toBeInTheDocument();
  });

  it('keeps the summary out of the way until it is asked for', () => {
    render(<CompactionNote summary="They asked about the fee." />);
    expect(screen.queryByText('They asked about the fee.')).not.toBeInTheDocument();
  });

  it('shows the summary when it is asked for', () => {
    render(<CompactionNote summary="They asked about the fee." />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('They asked about the fee.')).toBeInTheDocument();
  });

  it('can be put away again', () => {
    render(<CompactionNote summary="They asked about the fee." />);
    fireEvent.click(screen.getByRole('button'));
    fireEvent.click(screen.getByRole('button'));
    expect(screen.queryByText('They asked about the fee.')).not.toBeInTheDocument();
  });

  it('says whether the summary is showing', () => {
    render(<CompactionNote summary="They asked about the fee." />);
    const toggle = screen.getByRole('button');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
  });

  it('does not offer to show a summary that is empty', () => {
    render(<CompactionNote summary="" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('still marks the compaction when the summary is empty', () => {
    render(<CompactionNote summary="" />);
    expect(screen.getByText(/summarised|summarized/i)).toBeInTheDocument();
  });
});
