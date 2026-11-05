export interface Alert {
  id: string;
  kind: string;
  person: string;
  severity: number;
  count: number;
  at: string;
  summary: string;
  acknowledged: boolean;
}

export interface AlertRow {
  id: string;
  level: 'low' | 'medium' | 'high' | 'critical';
  summary: string;
  when: string;
  acknowledged: boolean;
  action: 'acknowledge' | 'none';
}

export interface PresentedAlerts {
  rows: AlertRow[];
  unacknowledged: number;
  needsAttention: boolean;
  emptyMessage: string;
}

const LEVELS: Record<number, AlertRow['level']> = {
  1: 'low',
  2: 'medium',
  3: 'high',
  4: 'critical',
};

const CRITICAL = 4;

export function presentAlerts(alerts: Alert[], now: Date): PresentedAlerts {
  const rows = [...alerts]
    .sort(
      (a, b) =>
        Number(a.acknowledged) - Number(b.acknowledged) ||
        b.severity - a.severity ||
        Date.parse(b.at) - Date.parse(a.at),
    )
    .map((alert) => ({
      id: alert.id,
      level: LEVELS[alert.severity] ?? 'low',
      summary: alert.summary,
      when: ago(alert.at, now),
      acknowledged: alert.acknowledged,
      action: alert.acknowledged ? ('none' as const) : ('acknowledge' as const),
    }));

  return {
    rows,
    unacknowledged: alerts.filter((alert) => !alert.acknowledged).length,
    // Acknowledged means someone has it; it is the unseen ones that demand attention.
    needsAttention: alerts.some((alert) => !alert.acknowledged && alert.severity >= CRITICAL),
    emptyMessage: rows.length === 0 ? 'Nothing has fired' : '',
  };
}

function ago(at: string, now: Date): string {
  const minutes = Math.round((now.getTime() - Date.parse(at)) / 60_000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
  const hours = Math.round(minutes / 60);
  return `${hours} hour${hours === 1 ? '' : 's'} ago`;
}
