import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { StoppingNotice } from './StoppingNotice';

describe('StoppingNotice', () => {
  it('says nothing when no stop was asked for', () => {
    const { container } = render(<StoppingNotice stopping={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says the stop has been asked for', () => {
    render(<StoppingNotice stopping />);
    expect(screen.getByText(/stopping/i)).toBeInTheDocument();
  });

  it('warns that the step in flight finishes first', () => {
    render(<StoppingNotice stopping />);
    expect(screen.getByText(/in flight|already started/i)).toBeInTheDocument();
  });

  it('is announced rather than left for the eye to find', () => {
    render(<StoppingNotice stopping />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
