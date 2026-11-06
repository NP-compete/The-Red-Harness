import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ExportButton } from './ExportButton';

let revoked: string[];
let clicked: { href: string; download: string }[];

beforeEach(() => {
  revoked = [];
  clicked = [];
  vi.stubGlobal('URL', {
    ...URL,
    createObjectURL: () => 'blob:made-up',
    revokeObjectURL: (url: string) => revoked.push(url),
  });
  // The download happens by clicking an anchor nobody can see, so
  // the test watches for that rather than for a navigation.
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    clicked.push({ href: this.href, download: this.download });
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function answering(ok = true, body = 'model,runs\ngpt-4o,12\n') {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok,
    blob: async () => new Blob([body], { type: 'text/csv' }),
    text: async () => body,
  } as unknown as Response);
}

describe('ExportButton', () => {
  it('offers the download', () => {
    answering();
    render(<ExportButton what="models" days={7} />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('asks the agent for the report it was given', async () => {
    const fetched = answering();
    render(<ExportButton what="models" days={7} />);
    await userEvent.click(screen.getByRole('button'));
    await waitFor(() =>
      expect(String(fetched.mock.calls[0][0])).toContain('what=models'),
    );
  });

  it('asks for the window being looked at', async () => {
    // Exporting a different period from the one on screen is the
    // kind of mistake nobody notices until the numbers are in a
    // slide.
    const fetched = answering();
    render(<ExportButton what="models" days={30} />);
    await userEvent.click(screen.getByRole('button'));
    await waitFor(() => expect(String(fetched.mock.calls[0][0])).toContain('days=30'));
  });

  it('saves it with a name that says what it is', async () => {
    answering();
    render(<ExportButton what="models" days={7} />);
    await userEvent.click(screen.getByRole('button'));
    await waitFor(() => expect(clicked[0].download).toBe('models-7d.csv'));
  });

  it('lets go of the file afterwards', async () => {
    // Every export leaks a blob until the tab closes otherwise.
    answering();
    render(<ExportButton what="models" days={7} />);
    await userEvent.click(screen.getByRole('button'));
    await waitFor(() => expect(revoked).toContain('blob:made-up'));
  });

  describe('when the agent will not produce it', () => {
    it('does not save an empty file', async () => {
      // A spreadsheet with nothing in it reads as "no usage",
      // which is a different answer from "this did not work".
      answering(false);
      render(<ExportButton what="models" days={7} />);
      await userEvent.click(screen.getByRole('button'));
      await waitFor(() => expect(clicked).toHaveLength(0));
    });

    it('says so', async () => {
      answering(false);
      render(<ExportButton what="models" days={7} />);
      await userEvent.click(screen.getByRole('button'));
      expect(await screen.findByRole('alert')).toBeInTheDocument();
    });
  });

  it('does not start a second export over the first', async () => {
    // Two clicks, two files with the same name, and the second
    // silently replaces the first in the downloads folder. Tested
    // against a request still in flight, because by the time a
    // finished click returns there is nothing left to observe.
    const fetched = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValue(new Promise(() => {}) as never);
    render(<ExportButton what="models" days={7} />);
    const button = screen.getByRole('button');

    await userEvent.click(button);
    expect(button).toBeDisabled();
    await userEvent.click(button);

    expect(fetched).toHaveBeenCalledTimes(1);
  });
});
