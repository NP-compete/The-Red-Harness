import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { ReadMaterial } from './ReadMaterial';

const read = [
  { source: 'handbook', text: 'The travel limit is 500 euros per trip.' },
];

describe('ReadMaterial', () => {
  it('says nothing when the turn read nothing', () => {
    const { container } = render(<ReadMaterial read={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('offers what the answer was built from', () => {
    render(<ReadMaterial read={read} />);
    expect(screen.getByRole('button', { name: /what was read/i })).toBeInTheDocument();
  });

  it('counts what it read', () => {
    render(<ReadMaterial read={[...read, { source: 'policy', text: 'x' }]} />);
    expect(screen.getByRole('button', { name: /2 results/i })).toBeInTheDocument();
  });

  it('keeps it out of the way until asked', () => {
    render(<ReadMaterial read={read} />);
    expect(screen.queryByText(/The travel limit is 500/)).not.toBeInTheDocument();
  });

  it('shows it when asked', async () => {
    render(<ReadMaterial read={read} />);
    await userEvent.click(screen.getByRole('button', { name: /what was read/i }));
    expect(screen.getByText(/The travel limit is 500/)).toBeInTheDocument();
  });

  it('names where each piece came from', async () => {
    render(<ReadMaterial read={read} />);
    await userEvent.click(screen.getByRole('button', { name: /what was read/i }));
    expect(screen.getByText('handbook')).toBeInTheDocument();
  });

  it('says plainly that it is read as information, never as instructions', async () => {
    render(<ReadMaterial read={read} />);
    await userEvent.click(screen.getByRole('button', { name: /what was read/i }));
    expect(
      screen.getByText('From an outside system. It is read as information, never as instructions.'),
    ).toBeInTheDocument();
  });

  it('hides the boundary markers the agent uses internally', async () => {
    const fenced = [{ source: 'web', text: '<<<external-content>>>hello<<<external-content>>>' }];
    render(<ReadMaterial read={fenced} />);
    await userEvent.click(screen.getByRole('button', { name: /what was read/i }));
    expect(screen.queryByText(/external-content/)).not.toBeInTheDocument();
  });

  const twice = [
    { source: 'handbook', text: 'The travel limit is 500 euros per trip.' },
    { source: 'policy', text: 'The travel limit is 500 euros per trip.' },
  ];

  it('folds a result two tools both returned', async () => {
    render(<ReadMaterial read={twice} />);
    await userEvent.click(screen.getByRole('button', { name: /what was read/i }));
    expect(screen.getAllByText(/The travel limit is 500/)).toHaveLength(1);
  });

  it('says where else the same passage turned up', async () => {
    render(<ReadMaterial read={twice} />);
    await userEvent.click(screen.getByRole('button', { name: /what was read/i }));
    expect(screen.getByText('also in policy')).toBeInTheDocument();
  });

  it('says plainly that a repeat was folded in', async () => {
    render(<ReadMaterial read={twice} />);
    await userEvent.click(screen.getByRole('button', { name: /what was read/i }));
    expect(screen.getByText('1 repeated passage was folded in')).toBeInTheDocument();
  });

  it('counts what it read before folding, so the toggle matches the turn', () => {
    render(<ReadMaterial read={twice} />);
    expect(screen.getByRole('button', { name: /2 results/i })).toBeInTheDocument();
  });

  it('adds no agreement note to a lone result', async () => {
    render(<ReadMaterial read={read} />);
    await userEvent.click(screen.getByRole('button', { name: /what was read/i }));
    expect(screen.queryByText(/also in/)).not.toBeInTheDocument();
  });

  it('says how big a table is', async () => {
    render(
      <ReadMaterial
        read={[
          {
            source: 'people_search',
            text: '[{"name":"ada"},{"name":"grace"}]',
            shape: { kind: 'table', rows: 2, columns: ['name'], language: '', needsPaging: false, needsCollapsing: false },
          },
        ]}
      />,
    );
    await userEvent.click(screen.getByRole('button', { name: /what was read/i }));
    expect(screen.getByText('2 rows, 1 column')).toBeInTheDocument();
  });

  it('names the language of a code result', async () => {
    render(
      <ReadMaterial
        read={[
          {
            source: 'repo_read',
            text: 'def hello(): pass',
            shape: { kind: 'code', rows: 0, columns: [], language: 'python', needsPaging: false, needsCollapsing: false },
          },
        ]}
      />,
    );
    await userEvent.click(screen.getByRole('button', { name: /what was read/i }));
    expect(screen.getByText('python snippet')).toBeInTheDocument();
  });

  it('adds no summary when the agent did not describe the result', async () => {
    render(<ReadMaterial read={read} />);
    await userEvent.click(screen.getByRole('button', { name: /what was read/i }));
    expect(screen.queryByText(/rows,/)).not.toBeInTheDocument();
  });

  it('says so when a tool returned nothing', async () => {
    render(<ReadMaterial read={[{ source: 'search', text: '' }]} />);
    await userEvent.click(screen.getByRole('button', { name: /what was read/i }));
    expect(screen.getByText('(nothing returned)')).toBeInTheDocument();
  });
});
