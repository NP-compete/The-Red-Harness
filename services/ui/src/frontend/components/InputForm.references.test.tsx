import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { InputForm } from './InputForm';

const known = vi.hoisted(() => ({
  useReferenceable: () => ({
    subagents: [{ name: 'curator', about: 'Finds data worth trusting' }],
    documents: [{ name: 'notes.md', about: '1.2 kB' }],
  }),
}));
vi.mock('../hooks/useReferenceable', () => known);
vi.mock('../hooks/useCommands', () => ({ useCommands: () => [] }));

const show = () =>
  render(<InputForm onSubmit={vi.fn()} isLoading={false} onCancel={vi.fn()} />);

describe('naming a specialist or a document in the composer', () => {
  it('offers the specialists on @', async () => {
    show();
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'ask @' } });
    expect(await screen.findByText('@curator')).toBeInTheDocument();
  });

  it('offers the documents on #', async () => {
    show();
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'see #' } });
    expect(await screen.findByText('#notes.md')).toBeInTheDocument();
  });

  it('finishes the reference in the composer when one is picked', async () => {
    show();
    const box = screen.getByRole('textbox');
    fireEvent.change(box, { target: { value: 'ask @cur' } });
    fireEvent.click(await screen.findByText('@curator'));
    await waitFor(() => expect(box).toHaveValue('ask @curator '));
  });

  it('does not send anything on its own', async () => {
    const onSubmit = vi.fn();
    render(<InputForm onSubmit={onSubmit} isLoading={false} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'ask @cur' } });
    fireEvent.click(await screen.findByText('@curator'));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
