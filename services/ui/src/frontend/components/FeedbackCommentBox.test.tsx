import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { FeedbackCommentBox, type FeedbackState } from './FeedbackButtons';

function state(overrides: Partial<FeedbackState> = {}): FeedbackState {
  return {
    existingFeedback: null,
    isSubmitting: false,
    showCommentInput: true,
    comment: '',
    disabled: false,
    handleThumbsUp: vi.fn(),
    handleThumbsDown: vi.fn(),
    handleCommentSubmit: vi.fn(),
    setComment: vi.fn(),
    cancelComment: vi.fn(),
    ...overrides,
  };
}

describe('FeedbackCommentBox', () => {
  it('asks what went wrong', () => {
    render(<FeedbackCommentBox fb={state()} />);
    expect(screen.getByText('What went wrong?')).toBeInTheDocument();
  });

  it('offers reasons rather than only a blank box', () => {
    render(<FeedbackCommentBox fb={state()} />);
    for (const reason of ['Wrong answer', 'Missed something', 'Too slow', 'Something else']) {
      expect(screen.getByRole('button', { name: reason })).toBeInTheDocument();
    }
  });

  it('fills the comment when a reason is picked', async () => {
    const setComment = vi.fn();
    render(<FeedbackCommentBox fb={state({ setComment })} />);
    await userEvent.click(screen.getByRole('button', { name: 'Wrong answer' }));
    expect(setComment).toHaveBeenCalledWith('Wrong answer');
  });

  it('shows which reason is picked', () => {
    render(<FeedbackCommentBox fb={state({ comment: 'Too slow' })} />);
    expect(screen.getByRole('button', { name: 'Too slow' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('leaves the other reasons unpicked', () => {
    render(<FeedbackCommentBox fb={state({ comment: 'Too slow' })} />);
    expect(screen.getByRole('button', { name: 'Wrong answer' })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
  });

  it('still lets someone write their own words', () => {
    render(<FeedbackCommentBox fb={state()} />);
    expect(screen.getByPlaceholderText('What went wrong? (optional)')).toBeInTheDocument();
  });

  it('shows nothing when it is not asking', () => {
    const { container } = render(<FeedbackCommentBox fb={state({ showCommentInput: false })} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows nothing once a rating has been given', () => {
    const { container } = render(<FeedbackCommentBox fb={state({ existingFeedback: 'down' })} />);
    expect(container).toBeEmptyDOMElement();
  });
});
