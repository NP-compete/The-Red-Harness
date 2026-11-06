import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Followups } from './Followups';

const uncovered = ['Also when must receipts be filed'];

describe('Followups', () => {
  it('says nothing when the question was fully answered', () => {
    const { container } = render(<Followups uncovered={[]} onAsk={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('offers the part that went unanswered', () => {
    render(<Followups uncovered={uncovered} onAsk={vi.fn()} />);
    expect(screen.getByRole('button', { name: /receipts/ })).toBeInTheDocument();
  });

  it('offers rather than instructs', () => {
    render(<Followups uncovered={uncovered} onAsk={vi.fn()} />);
    expect(screen.getByText('You could ask next')).toBeInTheDocument();
  });

  it('asks the whole question when picked, not the shortened label', async () => {
    const long = ['Also when must receipts be filed for travel booked through the agency'];
    const onAsk = vi.fn();
    render(<Followups uncovered={long} onAsk={onAsk} />);
    await userEvent.click(screen.getByRole('button'));
    expect(onAsk).toHaveBeenCalledWith(long[0]);
  });

  it('shortens a long suggestion on the chip itself', () => {
    const long = ['Also when must receipts be filed for travel booked through the agency'];
    render(<Followups uncovered={long} onAsk={vi.fn()} />);
    expect(screen.getByRole('button').textContent).toContain('…');
  });

  it('offers each unanswered part', () => {
    render(<Followups uncovered={['One thing', 'Another thing']} onAsk={vi.fn()} />);
    expect(screen.getAllByRole('button')).toHaveLength(2);
  });

  it('does not steal the cursor from the message box', () => {
    render(<Followups uncovered={uncovered} onAsk={vi.fn()} />);
    expect(document.activeElement).toBe(document.body);
  });
});
