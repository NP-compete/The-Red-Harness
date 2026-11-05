import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { StopButton } from './StopButton';

describe('StopButton', () => {
  it('offers to stop a run that is thinking', () => {
    render(<StopButton stage="thinking" onStop={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Cancel streaming' })).toBeEnabled();
  });

  it('stops the run when pressed', async () => {
    const onStop = vi.fn();
    render(<StopButton stage="thinking" onStop={onStop} />);
    await userEvent.click(screen.getByRole('button', { name: 'Cancel streaming' }));
    expect(onStop).toHaveBeenCalled();
  });

  it('promises only what it can deliver mid-write', () => {
    render(<StopButton stage="calling-tool" tool="send_email" reversible={false} onStop={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Stop after this step' })).toBeInTheDocument();
  });

  it('says plainly what stopping mid-write will not undo', async () => {
    render(<StopButton stage="calling-tool" tool="send_email" reversible={false} onStop={vi.fn()} />);
    await userEvent.hover(screen.getByRole('button'));
    expect(screen.getByRole('button')).toHaveAttribute(
      'title',
      expect.stringContaining('send_email'),
    );
  });

  it('stops plainly when the tool in flight can be undone', () => {
    render(<StopButton stage="calling-tool" tool="search" reversible onStop={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Cancel streaming' })).toBeInTheDocument();
  });

  it('asks for no confirmation while merely thinking', () => {
    render(<StopButton stage="thinking" onStop={vi.fn()} />);
    expect(screen.getByRole('button')).not.toHaveAttribute('title');
  });

  it('shows nothing once the run is done', () => {
    const { container } = render(<StopButton stage="done" onStop={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('does not stop a run that is not yours', () => {
    render(<StopButton stage="thinking" isOwner={false} onStop={vi.fn()} />);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('says why it will not stop someone else"s run', () => {
    render(<StopButton stage="thinking" isOwner={false} onStop={vi.fn()} />);
    expect(screen.getByRole('button')).toHaveAttribute(
      'title',
      'This run is not yours to stop.',
    );
  });

  it('lets an operator stop a run that is not theirs', () => {
    render(<StopButton stage="thinking" isOwner={false} isOperator onStop={vi.fn()} />);
    expect(screen.getByRole('button')).toBeEnabled();
  });
});
