import i18n from '../i18n';
export interface UsageTotals {
  tokens: number;
  approvals: number;
  refusals: number;
  runs: number;
}

export interface Usage {
  totals: UsageTotals;
  perTeam: Record<string, { tokens: number; runs: number }>;
  discloses: boolean;
  period: string;
}

export interface HeadlineRow {
  label: string;
  value: string;
}

export interface TeamRow {
  name: string;
  tokens: string;
  share: string;
}

export interface PresentedUsage {
  period: string;
  headline: HeadlineRow[];
  teams: TeamRow[];
  disclosure: string;
}

export function presentUsage(usage: Usage): PresentedUsage {
  const total = Object.values(usage.perTeam).reduce((sum, team) => sum + team.tokens, 0);

  return {
    period: usage.period,
    // Runs first: tokens are an implementation detail of what people did.
    headline: [
      { label: i18n.t('usage.runs'), value: count(usage.totals.runs) },
      { label: i18n.t('usage.tokens'), value: count(usage.totals.tokens) },
      { label: i18n.t('usage.askedFirst'), value: count(usage.totals.approvals) },
      { label: i18n.t('usage.refused'), value: count(usage.totals.refusals) },
    ],
    teams: Object.entries(usage.perTeam)
      .sort(([, a], [, b]) => b.tokens - a.tokens)
      .map(([name, figures]) => ({
        name,
        tokens: count(figures.tokens),
        share: total === 0 ? '0%' : `${Math.round((figures.tokens / total) * 100)}%`,
      })),
    disclosure: usage.discloses
      ? 'This report names individuals.'
      : 'No individual is named in this report.',
  };
}

function count(value: number): string {
  return value.toLocaleString('en-US');
}
