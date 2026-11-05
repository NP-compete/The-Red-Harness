import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MessageProvenance } from './MessageProvenance';

const SPENT = 'This run has spent 0.60 USD of its 1.00 USD limit.';

describe('MessageProvenance', () => {
  it('says nothing about an answer there is nothing to say about', () => {
    const { container } = render(<MessageProvenance provenance={{}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('names the model that answered', () => {
    render(<MessageProvenance provenance={{ model: 'gemini-3.8-flash' }} />);
    expect(screen.getByText('gemini-3.8-flash')).toBeInTheDocument();
  });

  it('passes on what the run was told about its spending', () => {
    render(<MessageProvenance provenance={{ spend_warning: SPENT }} />);
    expect(screen.getByText(SPENT)).toBeInTheDocument();
  });

  it('shows spending as a warning, not as a footnote', () => {
    // A run most of the way through its allowance is about to stop.
    // Printed in the same grey as "from cache" it reads as trivia.
    render(<MessageProvenance provenance={{ spend_warning: SPENT }} />);
    expect(screen.getByText(SPENT).className).toMatch(/amber/);
  });

  it('shows the spending warning on its own, with no model to go with it', () => {
    const { container } = render(<MessageProvenance provenance={{ spend_warning: SPENT }} />);
    expect(container).not.toBeEmptyDOMElement();
  });

  it('says nothing about spending on a run that stayed well inside', () => {
    render(<MessageProvenance provenance={{ model: 'gemini-3.8-flash' }} />);
    expect(screen.queryByText(/has spent/i)).not.toBeInTheDocument();
  });
});
