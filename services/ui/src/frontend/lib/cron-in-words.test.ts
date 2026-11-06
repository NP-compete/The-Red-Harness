import { describe, expect, it } from 'vitest';

import { cronInWords, nextRunInWords } from './cron-in-words';

describe('saying a cron expression out loud', () => {
  it('names the weekday shorthand as weekdays', () => {
    // The one the agent writes most, from "every weekday at 8".
    expect(cronInWords('0 8 * * 1-5')).toBe('every weekday at 08:00');
  });

  it('says every day when no day is named', () => {
    expect(cronInWords('0 8 * * *')).toBe('every day at 08:00');
  });

  it('names a single day', () => {
    expect(cronInWords('30 9 * * 1')).toBe('every Monday at 09:30');
  });

  it('lists several days', () => {
    expect(cronInWords('0 7 * * 1,3,5')).toBe(
      'every Monday, Wednesday and Friday at 07:00'
    );
  });

  it('treats 7 as Sunday, as cron does', () => {
    expect(cronInWords('0 7 * * 7')).toBe('every Sunday at 07:00');
  });

  it('handles the minute and hour steps', () => {
    expect(cronInWords('* * * * *')).toBe('every minute');
    expect(cronInWords('*/15 * * * *')).toBe('every 15 minutes');
    expect(cronInWords('0 */6 * * *')).toBe('every 6 hours');
  });

  it('distinguishes on the hour from a minute past', () => {
    expect(cronInWords('0 * * * *')).toBe('every hour, on the hour');
    expect(cronInWords('20 * * * *')).toBe('every hour at 20 minutes past');
  });

  it('handles a day of the month and a yearly date', () => {
    expect(cronInWords('0 9 1 * *')).toBe('on the 1st of every month at 09:00');
    expect(cronInWords('0 9 2 * *')).toBe('on the 2nd of every month at 09:00');
    expect(cronInWords('0 9 11 * *')).toBe('on the 11th of every month at 09:00');
    expect(cronInWords('0 0 25 12 *')).toBe('every 25th of December at 00:00');
  });

  it('pads the clock so times line up when read in a column', () => {
    expect(cronInWords('5 7 * * *')).toBe('every day at 07:05');
  });

  describe('what it refuses to paraphrase', () => {
    // A wrong description of when something runs is worse than the
    // expression: the expression looks like something to check.
    it('hands back anything with the wrong number of fields', () => {
      expect(cronInWords('0 8 * *')).toBe('0 8 * *');
      expect(cronInWords('0 0 8 * * 1-5')).toBe('0 0 8 * * 1-5');
    });

    it('hands back ranges and steps it does not model', () => {
      expect(cronInWords('0 8-17 * * *')).toBe('0 8-17 * * *');
      expect(cronInWords('0 8 */2 * *')).toBe('0 8 */2 * *');
      expect(cronInWords('0 8 * * MON-FRI')).toBe('0 8 * * MON-FRI');
    });

    it('hands back out-of-range numbers rather than inventing a time', () => {
      expect(cronInWords('0 99 * * *')).toBe('0 99 * * *');
      expect(cronInWords('0 9 99 * *')).toBe('0 9 99 * *');
    });
  });
});

describe('saying when the next run falls', () => {
  const now = new Date('2026-11-01T13:00:00Z');

  it('uses today and tomorrow where they are clearer than a date', () => {
    expect(nextRunInWords('2026-11-01T18:00:00Z', now)).toBe('today at 18:00 UTC');
    expect(nextRunInWords('2026-11-02T08:00:00Z', now)).toBe(
      'tomorrow at 08:00 UTC'
    );
  });

  it('names the day inside the coming week', () => {
    expect(nextRunInWords('2026-11-04T08:00:00Z', now)).toBe(
      'Wednesday at 08:00 UTC'
    );
  });

  it('gives a date once a day name would be ambiguous', () => {
    expect(nextRunInWords('2026-11-20T08:00:00Z', now)).toBe(
      '20 November at 08:00 UTC'
    );
  });

  it('says nothing when there is no next run', () => {
    expect(nextRunInWords(null, now)).toBe('');
  });

  it('hands back an unparseable timestamp rather than guessing', () => {
    expect(nextRunInWords('not a date', now)).toBe('not a date');
  });
});
