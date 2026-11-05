import { describe, expect, it } from 'vitest';

import { presentChargeback } from '@/lib/cost-attribution-view';

const charges = [
  {
    runId: 'r1',
    chargedTo: 'quarterly',
    person: 'ana',
    amount: 1.5,
    breakdown: { main: 1.0, researcher: 0.5 },
  },
  { runId: 'r2', chargedTo: 'quarterly', person: 'bo', amount: 2.5, breakdown: { main: 2.5 } },
  { runId: 'r3', chargedTo: 'platform', person: 'ana', amount: 0.25, breakdown: { main: 0.25 } },
];

describe('presentChargeback', () => {
  it('groups spending by who pays', () => {
    expect(presentChargeback(charges, 'USD').rows.map((row) => row.chargedTo)).toEqual([
      'quarterly',
      'platform',
    ]);
  });

  it('totals each payer', () => {
    expect(presentChargeback(charges, 'USD').rows[0].total).toBe('$4.00');
  });

  it('puts the largest payer first', () => {
    expect(presentChargeback(charges, 'USD').rows[0].chargedTo).toBe('quarterly');
  });

  it('counts the runs behind each total', () => {
    expect(presentChargeback(charges, 'USD').rows[0].runs).toBe(2);
  });

  it('gives the overall total', () => {
    expect(presentChargeback(charges, 'USD').total).toBe('$4.25');
  });

  it('shows how much went to subagents', () => {
    expect(presentChargeback(charges, 'USD').rows[0].subagentShare).toBe('13%');
  });

  it('shows nothing for subagents when there were none', () => {
    expect(presentChargeback(charges, 'USD').rows[1].subagentShare).toBe('');
  });

  it('names the people behind a payer so a total is traceable', () => {
    expect(presentChargeback(charges, 'USD').rows[0].people).toEqual(['ana', 'bo']);
  });

  it('does not repeat a person who ran several times', () => {
    const repeated = [charges[0], { ...charges[0], runId: 'r4' }];
    expect(presentChargeback(repeated, 'USD').rows[0].people).toEqual(['ana']);
  });

  it('marks platform spending so it is not mistaken for a team', () => {
    expect(presentChargeback(charges, 'USD').rows[1].unattributed).toBe(true);
  });

  it('does not mark a real payer as unattributed', () => {
    expect(presentChargeback(charges, 'USD').rows[0].unattributed).toBe(false);
  });

  it('formats another currency', () => {
    expect(presentChargeback(charges, 'EUR').total).toBe('€4.25');
  });

  it('says plainly when nothing has been spent', () => {
    expect(presentChargeback([], 'USD').emptyMessage).toBe('No spending recorded');
  });
});
