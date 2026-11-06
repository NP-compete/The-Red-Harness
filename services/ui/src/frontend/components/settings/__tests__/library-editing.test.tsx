import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { MyLibrary } from '../MyLibrary';
import * as api from '../../../services/knowledge-api';

/**
 * Changing a note from the browser.
 *
 * The route to do it existed and nothing could reach it, so
 * fixing a typo still meant deleting the note and writing it
 * again — losing its id and anything pointing at it.
 *
 * A shared document is listed here too and cannot be changed.
 * Offering a save button that will be refused is worse than
 * offering none.
 */

afterEach(() => vi.restoreAllMocks());

const library = () =>
  vi.spyOn(api, 'readLibrary').mockResolvedValue({
    documents: [{ id: 'user:1', title: 'My note', bytes: 10 }],
    team: [{ id: 'corpus:policy', title: 'Policy', bytes: 20, team: 'core' }],
    used_bytes: 30,
    limit_bytes: 1000,
  } as never);

describe('editing a note', () => {
  it('offers a way in', async () => {
    library();
    render(<MyLibrary />);
    await waitFor(() => expect(screen.getByText('My note')).toBeTruthy());
    expect(screen.getByRole('button', { name: /edit .*My note/i })).toBeTruthy();
  });

  it('shows what the note currently says', async () => {
    library();
    vi.spyOn(api, 'readDocument').mockResolvedValue({
      id: 'user:1', title: 'My note', text: 'the original text', editable: true,
    });
    render(<MyLibrary />);
    await waitFor(() => expect(screen.getByText('My note')).toBeTruthy());
    await userEvent.click(screen.getByRole('button', { name: /edit .*My note/i }));
    await waitFor(() =>
      expect(screen.getByDisplayValue('the original text')).toBeTruthy(),
    );
  });

  it('saves the change', async () => {
    library();
    vi.spyOn(api, 'readDocument').mockResolvedValue({
      id: 'user:1', title: 'My note', text: 'old', editable: true,
    });
    const saved = vi.spyOn(api, 'editInLibrary').mockResolvedValue({ ok: true });

    render(<MyLibrary />);
    await waitFor(() => expect(screen.getByText('My note')).toBeTruthy());
    await userEvent.click(screen.getByRole('button', { name: /edit .*My note/i }));
    const box = await screen.findByDisplayValue('old');
    await userEvent.clear(box);
    await userEvent.type(box, 'new');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => expect(saved).toHaveBeenCalledWith('user:1', 'My note', 'new'));
  });

  it('shows the agent its own words when it refuses', async () => {
    // "4 of 10 bytes used" is actionable; "could not save" is
    // somebody guessing which rule they hit.
    library();
    vi.spyOn(api, 'readDocument').mockResolvedValue({
      id: 'user:1', title: 'My note', text: 'old', editable: true,
    });
    vi.spyOn(api, 'editInLibrary').mockResolvedValue({
      ok: false, detail: 'storing 90 more bytes would put you over your limit',
    });

    render(<MyLibrary />);
    await waitFor(() => expect(screen.getByText('My note')).toBeTruthy());
    await userEvent.click(screen.getByRole('button', { name: /edit .*My note/i }));
    await screen.findByDisplayValue('old');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() =>
      expect(screen.getByText(/over your limit/i)).toBeTruthy(),
    );
  });
});

describe('a document that is not yours', () => {
  it('offers no way to edit it', async () => {
    library();
    render(<MyLibrary />);
    await waitFor(() => expect(screen.getByText('Policy')).toBeTruthy());
    expect(screen.queryByRole('button', { name: /edit .*Policy/i })).toBeNull();
  });
});

describe('when the deployment keeps no personal documents', () => {
  it('says so rather than rendering an empty section', async () => {
    // The agent answers 404 because the feature is absent, not
    // refused, and `readLibrary` turns that into `null`. The
    // section is listed whatever the deployment keeps, so
    // rendering nothing left a heading above empty space and no
    // way to tell "off" from "broken".
    vi.spyOn(api, 'readLibrary').mockResolvedValue(null);

    render(<MyLibrary />);

    expect(
      await screen.findByText(/does not keep personal documents/),
    ).toBeInTheDocument();
  });
});
