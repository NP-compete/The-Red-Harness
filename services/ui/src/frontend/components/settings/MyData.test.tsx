/**
 * Taking a copy of what is held, and asking for it to go.
 *
 * Deletion is the one action nobody can undo by asking again,
 * so it is shown before it is done: what would go, what would
 * survive, and what is kept whatever anybody asks. Then a
 * confirmation that is a decision rather than a reflex.
 *
 * The export names what it could not collect. A short file
 * that looks complete teaches somebody to stop asking, which
 * is a worse outcome than a file that admits a gap.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MyData } from './MyData';
import * as api from '../../services/my-data-api';

const PREVIEW = {
  subject: 'johnwick',
  delete: { documents: ['user:1'], artifacts: ['tally'] },
  kept: { documents: ['team:1'] },
  retained: { audit: ['a1'] },
  counts: { documents: 1, artifacts: 1 },
  notes: ['The audit trail is retained.'],
};

function offering(preview = PREVIEW) {
  vi.spyOn(api, 'previewDeletion').mockResolvedValue(preview as never);
  return vi.spyOn(api, 'deleteMyData').mockResolvedValue({
    counts: { documents: 1, artifacts: 1 },
    failed: {},
  } as never);
}

describe('MyData', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('says nothing while it is still asking', () => {
    vi.spyOn(api, 'previewDeletion').mockReturnValue(new Promise(() => {}) as never);
    const { container } = render(<MyData />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows nothing when the agent cannot answer', async () => {
    // An older agent that has never been asked is not a
    // person with no data.
    vi.spyOn(api, 'previewDeletion').mockResolvedValue(null);
    const { container } = render(<MyData />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it('offers a copy', async () => {
    offering();
    render(<MyData />);
    expect(await screen.findByTestId('take-a-copy')).toBeInTheDocument();
  });

  it('says how much would be removed', async () => {
    offering();
    render(<MyData />);
    expect(await screen.findByText(/2/)).toBeInTheDocument();
  });

  it('says what would survive', async () => {
    // Shared content belongs to the team as much as to
    // whoever happened to add it, and somebody expecting it
    // to go needs to know before they ask.
    offering();
    render(<MyData />);
    expect(await screen.findByText(/team/i)).toBeInTheDocument();
  });

  it('says what is kept whatever anybody asks', async () => {
    offering();
    render(<MyData />);
    expect(await screen.findByText(/audit trail is retained/i)).toBeInTheDocument();
  });
});

describe('asking for it to go', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('does not delete on the first click', async () => {
    // One click away from irreversible is not a decision,
    // it is a reflex.
    const deleting = offering();
    render(<MyData />);
    await userEvent.click(await screen.findByTestId('delete-everything'));
    expect(deleting).not.toHaveBeenCalled();
  });

  it('asks for confirmation', async () => {
    offering();
    render(<MyData />);
    await userEvent.click(await screen.findByTestId('delete-everything'));
    expect(screen.getByTestId('confirm-delete')).toBeInTheDocument();
  });

  it('deletes once it is confirmed', async () => {
    const deleting = offering();
    render(<MyData />);
    await userEvent.click(await screen.findByTestId('delete-everything'));
    await userEvent.click(screen.getByTestId('confirm-delete'));
    await waitFor(() => expect(deleting).toHaveBeenCalled());
  });

  it('can be backed out of', async () => {
    const deleting = offering();
    render(<MyData />);
    await userEvent.click(await screen.findByTestId('delete-everything'));
    await userEvent.click(screen.getByTestId('cancel-delete'));
    expect(screen.queryByTestId('confirm-delete')).not.toBeInTheDocument();
    expect(deleting).not.toHaveBeenCalled();
  });

  it('says what went', async () => {
    offering();
    render(<MyData />);
    await userEvent.click(await screen.findByTestId('delete-everything'));
    await userEvent.click(screen.getByTestId('confirm-delete'));
    expect(await screen.findByRole('status')).toBeInTheDocument();
  });

  it('says plainly when a store would not let go', async () => {
    // Reporting success for a deletion that did not happen
    // is the one outcome nobody recovers from, because they
    // stop asking.
    vi.spyOn(api, 'previewDeletion').mockResolvedValue(PREVIEW as never);
    vi.spyOn(api, 'deleteMyData').mockResolvedValue({
      counts: { artifacts: 1 },
      failed: { documents: 'store is down' },
    } as never);

    render(<MyData />);
    await userEvent.click(await screen.findByTestId('delete-everything'));
    await userEvent.click(screen.getByTestId('confirm-delete'));
    expect(await screen.findByRole('alert')).toHaveTextContent(/documents/i);
  });
});

describe('it is actually on the page', () => {
  it('the profile section mounts it', async () => {
    // Beside the other irreversible action, where somebody
    // already goes looking.
    const source = await import('./ProfileSection?raw');
    expect(String(source.default)).toContain('<MyData');
  });
});

describe('what the action does not cover', () => {
  beforeEach(() => vi.restoreAllMocks());

  const WITH_GAP = {
    ...PREVIEW,
    not_included: { memory: 'listed and removable on the personalisation page' },
  };

  it('names what will not go', async () => {
    // Somebody reading "delete everything" will believe
    // memory went with it. Being told afterwards is no use.
    vi.spyOn(api, 'previewDeletion').mockResolvedValue(WITH_GAP as never);
    render(<MyData />);
    expect(await screen.findByText(/memory/i)).toBeInTheDocument();
  });

  it('says where to go for it instead', async () => {
    vi.spyOn(api, 'previewDeletion').mockResolvedValue(WITH_GAP as never);
    render(<MyData />);
    expect(await screen.findByText(/personalisation page/i)).toBeInTheDocument();
  });

  it('does not claim to delete everything', async () => {
    // The label has to match what the button does.
    vi.spyOn(api, 'previewDeletion').mockResolvedValue(WITH_GAP as never);
    render(<MyData />);
    const button = await screen.findByTestId('delete-everything');
    expect(button.textContent?.toLowerCase()).not.toContain('everything');
  });

  it('does claim it when nothing is left out', async () => {
    vi.spyOn(api, 'previewDeletion').mockResolvedValue({
      ...PREVIEW,
      not_included: {},
    } as never);
    render(<MyData />);
    const button = await screen.findByTestId('delete-everything');
    expect(button.textContent?.toLowerCase()).toContain('everything');
  });
});
