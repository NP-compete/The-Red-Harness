/**
 * Where the month is heading, when it is heading somewhere bad.
 *
 * The daily allowance works as a brake: you are stopped, you
 * wait a day, you carry on. A monthly budget does not. Running
 * out on the 22nd is not a pause, it is a team that cannot work
 * until the 1st — so it has to be said while there is still a
 * month left to change something.
 *
 * Which is also why only the bad case is shown. "On track" is
 * the answer every month until the month it is not, and a row
 * that says the same thing thirty times is a row nobody reads
 * on the thirty-first.
 */

export interface ForecastReport {
  verdict: 'on-track' | 'will-overrun' | 'exhausted';
  per_day: string;
  projected_total: string;
  remaining: string;
  exhausted_on: string | null;
  spent: string;
  limit: string;
}

export interface ForecastView {
  whose: 'person' | 'team';
  spent: boolean;
  perDay: string;
  projectedTotal: string;
  limit: string;
  exhaustedOn: string | null;
}

function worthSaying(report: ForecastReport | null): boolean {
  return report?.verdict === 'will-overrun' || report?.verdict === 'exhausted';
}

function asView(
  report: ForecastReport,
  whose: 'person' | 'team',
): ForecastView {
  return {
    whose,
    spent: report.verdict === 'exhausted',
    perDay: report.per_day,
    projectedTotal: report.projected_total,
    limit: report.limit,
    exhaustedOn: report.exhausted_on,
  };
}

export function describeForecast(
  person: ForecastReport | null,
  team: ForecastReport | null,
): ForecastView | null {
  const mine = worthSaying(person) ? person : null;
  const ours = worthSaying(team) ? team : null;

  // A budget already spent outranks one merely heading over:
  // one of them is a prediction and the other has already
  // happened.
  if (ours?.verdict === 'exhausted' && mine?.verdict !== 'exhausted') {
    return asView(ours, 'team');
  }

  // Otherwise theirs first. It is the one they can act on —
  // being told the team is over sends somebody to ask
  // colleagues to stop, which fixes nothing on its own.
  if (mine) return asView(mine, 'person');
  if (ours) return asView(ours, 'team');
  return null;
}
