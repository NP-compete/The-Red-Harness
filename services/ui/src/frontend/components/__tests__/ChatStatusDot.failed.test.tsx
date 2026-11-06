import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ChatStatusDot } from '../ChatStatusDot';

describe('ChatStatusDot — a run that died', () => {
  it('marks the conversation so it can be found again', () => {
    render(<ChatStatusDot activity="failed" />);
    expect(screen.getByRole('img')).toHaveAccessibleName(/stopped/i);
  });

  it('does not pulse: there is nothing still happening', () => {
    const { container } = render(<ChatStatusDot activity="failed" />);
    expect(container.querySelector('.animate-ping')).toBeNull();
  });

  it('still shows nothing for a finished conversation', () => {
    const { container } = render(<ChatStatusDot activity="idle" />);
    expect(container).toBeEmptyDOMElement();
  });
});
