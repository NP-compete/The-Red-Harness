import { describe, expect, it } from 'vitest';

import { describeInbound } from './inbound-view';

const SHUT = { enabled: false, auth_mode: '', published_tools: 0, limits: null };
const OPEN = {
  enabled: true,
  auth_mode: 'service_token',
  published_tools: 2,
  limits: { per_second: 2, burst: 10, daily_spend: '5.00' },
};

describe('describeInbound', () => {
  describe('a door that is shut', () => {
    it('is reported as shut', () => {
      expect(describeInbound(SHUT)?.open).toBe(false);
    });

    it('raises no concern', () => {
      // Every deployment has this shut. A warning here is one
      // that appears everywhere and is read nowhere.
      expect(describeInbound(SHUT)?.unlimited).toBe(false);
    });
  });

  describe('a door that is open', () => {
    it('is reported as open', () => {
      expect(describeInbound(OPEN)?.open).toBe(true);
    });

    it('says whose authority an inbound run carries', () => {
      expect(describeInbound(OPEN)?.authMode).toBe('service_token');
    });

    it('says how many tools it publishes', () => {
      expect(describeInbound(OPEN)?.publishedTools).toBe(2);
    });

    it('says the rate', () => {
      expect(describeInbound(OPEN)?.rate).toBe('2/s, burst 10');
    });

    it('says the daily cap', () => {
      expect(describeInbound(OPEN)?.dailySpend).toBe('5.00');
    });

    it('is not flagged when it has limits', () => {
      expect(describeInbound(OPEN)?.unlimited).toBe(false);
    });
  });

  describe('a door that is open with nothing behind it', () => {
    const wide = { ...OPEN, limits: null };

    it('is flagged', () => {
      // One caller away from the deployment's budget, and not
      // visible anywhere else.
      expect(describeInbound(wide)?.unlimited).toBe(true);
    });

    it('has no rate to show', () => {
      expect(describeInbound(wide)?.rate).toBe(null);
    });
  });

  describe('an open door with a rate but no cap', () => {
    const partly = { ...OPEN, limits: { per_second: 2, burst: 2, daily_spend: null } };

    it('is still flagged', () => {
      // A rate limit does nothing about a caller going at exactly
      // the agreed rate and spending the month's budget by
      // Thursday.
      expect(describeInbound(partly)?.unlimited).toBe(true);
    });

    it('shows the rate it does have', () => {
      expect(describeInbound(partly)?.rate).toBe('2/s, burst 2');
    });
  });

  describe('an agent that could not say', () => {
    it('reports nothing rather than guessing', () => {
      expect(describeInbound(null)).toBe(null);
    });

    it('treats a reply missing the field as no answer', () => {
      expect(describeInbound({} as never)).toBe(null);
    });
  });
});
