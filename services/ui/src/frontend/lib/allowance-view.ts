/**
 * What this person has left to spend today.
 *
 * Shown only where there is a cap. A row reading "you have
 * spent 1.25 of unlimited" is noise on every page of every
 * deployment that caps nothing, and noise is what people stop
 * reading before the one that mattered.
 */

import type { ForecastReport } from './forecast-view';

export interface AllowanceSide {
  spent: string;
  limit: string | null;
  remaining: string | null;
  nearly_out: boolean;
}

export interface AllowanceReport {
  person: AllowanceSide;
  team: AllowanceSide | null;
  team_name: string | null;
  unreadable: boolean;
  // Optional: an agent that predates the monthly budget
  // reports a day and nothing else, and that is not somebody
  // with no month.
  forecast?: {
    person: ForecastReport | null;
    team: ForecastReport | null;
  } | null;
}

export interface AllowanceView {
  person: AllowanceSide;
  team: AllowanceSide | null;
  teamName: string | null;
  warn: boolean;
}

export function describeMyAllowance(
  report: AllowanceReport | null,
): AllowanceView | null {
  if (!report || typeof report.person?.spent !== 'string') return null;

  // Showing a full allowance would be a guess, and the guess
  // happens to be the reassuring direction.
  if (report.unreadable) return null;

  const capped = report.person.limit !== null || report.team?.limit != null;
  if (!capped) return null;

  return {
    person: report.person,
    team: report.team,
    teamName: report.team_name,
    // Either side. A team running out is not theirs to fix,
    // but they need to know before starting something long.
    warn: Boolean(report.person.nearly_out || report.team?.nearly_out),
  };
}
