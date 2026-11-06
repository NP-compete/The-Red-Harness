/**
 * Where the month is heading, as a sentence somebody can act on.
 *
 * The daily figure works as a brake: you are stopped, you wait a
 * day, you carry on. A monthly budget does not work that way.
 * Running out on the 22nd is not a pause, it is a team that
 * cannot work until the 1st — so it has to be said while there
 * is still a month left to change something.
 *
 * Which means the only version worth showing is the one that is
 * going wrong. "On track" is the answer every month until the
 * month it is not, and a row that says the same thing thirty
 * times is a row nobody is reading on the thirty-first.
 */

import { describe, expect, it } from 'vitest';

import { describeForecast, type ForecastReport } from './forecast-view';

const onTrack: ForecastReport = {
  verdict: 'on-track',
  per_day: '1.00',
  projected_total: '31.00',
  remaining: '90.00',
  exhausted_on: null,
  spent: '10.00',
  limit: '100.00',
};

const overrunning: ForecastReport = {
  verdict: 'will-overrun',
  per_day: '6.00',
  projected_total: '186.00',
  remaining: '40.00',
  exhausted_on: '2026-03-16',
  spent: '60.00',
  limit: '100.00',
};

const exhausted: ForecastReport = {
  verdict: 'exhausted',
  per_day: '10.00',
  projected_total: '120.00',
  remaining: '0.00',
  exhausted_on: null,
  spent: '120.00',
  limit: '100.00',
};

describe('when there is nothing to warn about', () => {
  it('shows nothing for a month that is on track', () => {
    expect(describeForecast(onTrack, null)).toBeNull();
  });

  it('shows nothing when there is no forecast at all', () => {
    expect(describeForecast(null, null)).toBeNull();
  });

  it('shows nothing for a shape it does not recognise', () => {
    expect(
      describeForecast({ verdict: 'something-else' } as never, null),
    ).toBeNull();
  });
});

describe('a month heading over', () => {
  it('is shown', () => {
    expect(describeForecast(overrunning, null)).not.toBeNull();
  });

  it('carries the date the budget runs out', () => {
    expect(describeForecast(overrunning, null)?.exhaustedOn).toBe('2026-03-16');
  });

  it('carries the daily burn, which is the thing to change', () => {
    expect(describeForecast(overrunning, null)?.perDay).toBe('6.00');
  });

  it('is about this person, not the team', () => {
    expect(describeForecast(overrunning, null)?.whose).toBe('person');
  });

  it('is a warning, not a stop', () => {
    expect(describeForecast(overrunning, null)?.spent).toBe(false);
  });
});

describe('a month already spent', () => {
  it('is shown', () => {
    expect(describeForecast(exhausted, null)).not.toBeNull();
  });

  it('says it is spent rather than predicting', () => {
    expect(describeForecast(exhausted, null)?.spent).toBe(true);
  });

  it('names no date, because the date has passed', () => {
    expect(describeForecast(exhausted, null)?.exhaustedOn).toBeNull();
  });
});

describe('the team as well as the person', () => {
  it("shows the team's month when only the team is overrunning", () => {
    expect(describeForecast(onTrack, overrunning)?.whose).toBe('team');
  });

  it('prefers their own when both are overrunning', () => {
    // Theirs is the one they can do something about. Being
    // told the team is over sends somebody to ask colleagues
    // to stop, which fixes nothing on its own.
    expect(describeForecast(overrunning, overrunning)?.whose).toBe('person');
  });

  it('prefers a budget already spent over one merely heading over', () => {
    // One of them is a prediction and the other has already
    // happened.
    expect(describeForecast(overrunning, exhausted)?.whose).toBe('team');
  });
});
