import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { UpdateBanner } from './UpdateBanner';

function show(over: Record<string, unknown> = {}) {
  const apply = vi.fn();
  const view = render(
    <UpdateBanner waiting={true} busy={false} onApply={apply} {...over} />,
  );
  return { ...view, apply };
}

describe('UpdateBanner', () => {
  it('says nothing when there is no new version', () => {
    const { container } = show({ waiting: false });
    expect(container).toBeEmptyDOMElement();
  });

  it('says so when one is waiting', () => {
    show();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('stays out of the way while a run is in flight', () => {
    // Interrupting somebody mid-answer to offer a version bump is
    // the wrong moment by any measure.
    const { container } = show({ busy: true });
    expect(container).toBeEmptyDOMElement();
  });

  it('says that applying it reloads the page', () => {
    show();
    expect(screen.getByText(/reload/i)).toBeInTheDocument();
  });

  it('applies only when asked', async () => {
    const { apply } = show();
    expect(apply).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: /reload/i }));
    expect(apply).toHaveBeenCalledOnce();
  });

  it('can be dismissed', async () => {
    const { container } = show();
    await userEvent.click(screen.getByRole('button', { name: /later|dismiss|not now/i }));
    expect(container).toBeEmptyDOMElement();
  });

  it('stays dismissed rather than returning on the next render', async () => {
    const { container, rerender, apply } = show();
    await userEvent.click(screen.getByRole('button', { name: /later|dismiss|not now/i }));
    rerender(<UpdateBanner waiting={true} busy={false} onApply={apply} />);
    expect(container).toBeEmptyDOMElement();
  });
});
