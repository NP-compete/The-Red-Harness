import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { SkillList } from './SkillList';

function answers(skills: unknown[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ skills }),
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

const GOOD = {
  name: 'data-discovery',
  description: 'Finds a dataset.',
  problem: '',
  agents: ['curator'],
  attached: true,
};

describe('SkillList', () => {
  it('shows what a skill is for', async () => {
    answers([GOOD]);
    render(<SkillList />);
    expect(await screen.findByText('Finds a dataset.')).toBeInTheDocument();
  });

  it('says when a skill could not be read', async () => {
    answers([{ ...GOOD, description: '', problem: 'Its SKILL.md could not be read' }]);
    render(<SkillList />);
    expect(await screen.findByText(/could not be read/)).toBeInTheDocument();
  });

  it('does not invent a problem for a skill that simply says little', async () => {
    answers([{ ...GOOD, description: '', problem: '' }]);
    render(<SkillList />);
    expect(await screen.findByText('data-discovery')).toBeInTheDocument();
    expect(screen.queryByText(/could not be read/)).not.toBeInTheDocument();
  });

  it('keeps describing the skills that are fine', async () => {
    answers([{ ...GOOD, name: 'broken', description: '', problem: 'Its SKILL.md could not be read' }, GOOD]);
    render(<SkillList />);
    expect(await screen.findByText('Finds a dataset.')).toBeInTheDocument();
  });
});
