import { describe, expect, it } from 'vitest';

import { describeMyAllowance } from './allowance-view';

const CAPPED = {
  person: { spent: '1.25', limit: '5.00', remaining: '3.75', nearly_out: false },
  team: { spent: '8.00', limit: '20.00', remaining: '12.00', nearly_out: false },
  team_name: 'platform',
  unreadable: false,
};

describe('describeMyAllowance', () => {
  it('says what is left', () => {
    expect(describeMyAllowance(CAPPED)?.person.remaining).toBe('3.75');
  });

  it('names the team the other figure belongs to', () => {
    expect(describeMyAllowance(CAPPED)?.teamName).toBe('platform');
  });

  describe('with no cap set', () => {
    const uncapped = {
      person: { spent: '1.25', limit: null, remaining: null, nearly_out: false },
      team: null,
      team_name: null,
      unreadable: false,
    };

    it('is not worth showing', () => {
      // A row saying "you have spent 1.25 of unlimited" is
      // noise on every page of every deployment that caps
      // nothing.
      expect(describeMyAllowance(uncapped)).toBe(null);
    });
  });

  describe('when the counter could not be read', () => {
    it('is not shown', () => {
      // Showing a full allowance would be a guess, and the
      // guess is the reassuring direction.
      expect(describeMyAllowance({ ...CAPPED, unreadable: true })).toBe(null);
    });
  });

  describe('nearly out', () => {
    it('is flagged', () => {
      const low = { ...CAPPED, person: { ...CAPPED.person, nearly_out: true } };
      expect(describeMyAllowance(low)?.warn).toBe(true);
    });

    it('is flagged when it is the team that is nearly out', () => {
      // Not theirs to fix, but they need to know before they
      // start something long.
      const low = { ...CAPPED, team: { ...CAPPED.team, nearly_out: true } };
      expect(describeMyAllowance(low)?.warn).toBe(true);
    });

    it('is not flagged with room to spare', () => {
      expect(describeMyAllowance(CAPPED)?.warn).toBe(false);
    });
  });

  describe('an agent that does not answer', () => {
    it('reports nothing rather than guessing', () => {
      expect(describeMyAllowance(null)).toBe(null);
    });
  });
});
