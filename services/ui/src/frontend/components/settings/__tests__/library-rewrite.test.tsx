import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { MyLibrary } from '../MyLibrary';
import * as api from '../../../services/knowledge-api';

/**
 * Asking for a selected passage to be rewritten.
 *
 * The note is open in a box and somebody highlights a paragraph
 * they are unhappy with. Three things about this are worth
 * pinning, and they are the three ways it costs somebody text
 * they wrote:
 *
 * - **Only the selection goes.** Sending the whole note and
 *   writing back the whole note means one clumsy paragraph gets
 *   the other nine rewritten as well.
 * - **Only the selection comes back.** The replacement lands in
 *   the range that was highlighted and the rest is untouched,
 *   character for character.
 * - **Nothing is saved.** The rewrite changes the box, not the
 *   note. Until somebody presses save there is an undo, which
 *   is the whole reason this is safe to offer.
 */

afterEach(() => vi.restoreAllMocks());

const library = () =>
  vi.spyOn(api, 'readLibrary').mockResolvedValue({
    documents: [{ id: 'user:1', title: 'My note', bytes: 10 }],
    team: [],
    used_bytes: 10,
    limit_bytes: 1000,
  } as never);

const NOTE = 'keep this. rewrite me. keep this too.';

/** Open the note and highlight `rewrite me.` inside it. */
async function openAndSelect(text = NOTE) {
  library();
  vi.spyOn(api, 'readDocument').mockResolvedValue({
    id: 'user:1', title: 'My note', text, editable: true,
  });
  render(<MyLibrary />);
  await waitFor(() => expect(screen.getByText('My note')).toBeTruthy());
  await userEvent.click(screen.getByRole('button', { name: /edit .*My note/i }));

  const box = (await screen.findByDisplayValue(text)) as HTMLTextAreaElement;
  const from = text.indexOf('rewrite me.');
  box.setSelectionRange(from, from + 'rewrite me.'.length);
  return box;
}

async function askFor(instruction: string) {
  await userEvent.type(
    screen.getByRole('textbox', { name: /what to change/i }),
    instruction,
  );
  await userEvent.click(screen.getByRole('button', { name: /rewrite selection/i }));
}

describe('rewriting a selection', () => {
  it('sends only the highlighted passage', async () => {
    const asked = vi
      .spyOn(api, 'rewriteSelection')
      .mockResolvedValue({ ok: true, text: 'rewritten.', reason: '' });

    await openAndSelect();
    await askFor('tighten it');

    await waitFor(() =>
      expect(asked).toHaveBeenCalledWith('rewrite me.', 'tighten it'),
    );
  });

  it('replaces only that passage and leaves the rest alone', async () => {
    vi.spyOn(api, 'rewriteSelection').mockResolvedValue({
      ok: true, text: 'rewritten.', reason: '',
    });

    const box = await openAndSelect();
    await askFor('tighten it');

    await waitFor(() =>
      expect(box.value).toBe('keep this. rewritten. keep this too.'),
    );
  });

  it('does not save the note', async () => {
    // The rewrite is a suggestion in a box. Saving it here would
    // take away the only undo somebody has.
    const saved = vi.spyOn(api, 'editInLibrary').mockResolvedValue({ ok: true });
    vi.spyOn(api, 'rewriteSelection').mockResolvedValue({
      ok: true, text: 'rewritten.', reason: '',
    });

    await openAndSelect();
    await askFor('tighten it');

    await waitFor(() => expect(screen.getByDisplayValue(/rewritten/)).toBeTruthy());
    expect(saved).not.toHaveBeenCalled();
  });

  it('leaves the text alone and says why when the agent refuses', async () => {
    vi.spyOn(api, 'rewriteSelection').mockResolvedValue({
      ok: false, text: '', reason: 'Nothing came back. Your text is unchanged.',
    });

    const box = await openAndSelect();
    await askFor('tighten it');

    await waitFor(() => expect(screen.getByText(/unchanged/i)).toBeTruthy());
    expect(box.value).toBe(NOTE);
  });

  it('asks for a selection rather than rewriting the whole note', async () => {
    // A rewrite of everything is not a bigger version of this
    // feature, it is a different and much worse one.
    const asked = vi.spyOn(api, 'rewriteSelection');

    library();
    vi.spyOn(api, 'readDocument').mockResolvedValue({
      id: 'user:1', title: 'My note', text: NOTE, editable: true,
    });
    render(<MyLibrary />);
    await waitFor(() => expect(screen.getByText('My note')).toBeTruthy());
    await userEvent.click(screen.getByRole('button', { name: /edit .*My note/i }));
    await screen.findByDisplayValue(NOTE);

    await askFor('tighten it');

    await waitFor(() =>
      expect(screen.getByText(/select the passage you want changed/i)).toBeTruthy(),
    );
    expect(asked).not.toHaveBeenCalled();
  });

  it('does not ask with no instruction', async () => {
    const asked = vi.spyOn(api, 'rewriteSelection');
    await openAndSelect();
    await userEvent.click(screen.getByRole('button', { name: /rewrite selection/i }));
    expect(asked).not.toHaveBeenCalled();
  });
});
