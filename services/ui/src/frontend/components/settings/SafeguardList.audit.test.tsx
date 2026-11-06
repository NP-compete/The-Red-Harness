import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { SafeguardList } from './SafeguardList';

function answers(body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => body }),
  );
}

const SAFEGUARDS = {
  pii: { enabled: true, entities: ['email'], trace_strategy: 'hash' },
  guardrail: { enabled: false },
  token_budget: { enabled: true },
  audit: { enabled: true },
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('SafeguardList — whether actions are recorded', () => {
  it('says when they are', async () => {
    answers(SAFEGUARDS);
    render(<SafeguardList />);
    expect(await screen.findByText('Audit')).toBeInTheDocument();
  });

  it('marks it off when it is off', async () => {
    answers({ ...SAFEGUARDS, audit: { enabled: false } });
    render(<SafeguardList />);
    const row = (await screen.findByText('Audit')).closest('li');
    expect(row).toHaveTextContent(/off/i);
  });

  it('still lists the other safeguards', async () => {
    answers(SAFEGUARDS);
    render(<SafeguardList />);
    expect(await screen.findByText('Audit')).toBeInTheDocument();
    expect(screen.getByText('Guardrail')).toBeInTheDocument();
  });

  it('copes with an agent that does not report it', async () => {
    const { audit, ...withoutAudit } = SAFEGUARDS;
    void audit;
    answers(withoutAudit);
    render(<SafeguardList />);
    expect(await screen.findByText('Guardrail')).toBeInTheDocument();
    expect(screen.queryByText('Audit')).not.toBeInTheDocument();
  });
});
