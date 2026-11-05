export interface ConsentReceipt {
  receiptId: string;
  purpose: string;
  granted: boolean;
  at: string;
  wording: string;
}

export interface ConsentRow {
  purpose: string;
  wording: string;
  granted: boolean;
  changed: string;
  changes: number;
  history: ConsentReceipt[];
  action: 'withdraw' | 'allow';
}

export interface PresentedConsentHistory {
  rows: ConsentRow[];
  summary: string;
}

const DAY = 86_400_000;

export function presentConsentHistory(
  receipts: ConsentReceipt[],
  now: Date,
): PresentedConsentHistory {
  const byPurpose = new Map<string, ConsentReceipt[]>();
  for (const receipt of receipts) {
    byPurpose.set(receipt.purpose, [...(byPurpose.get(receipt.purpose) ?? []), receipt]);
  }

  const rows = [...byPurpose.entries()]
    .map(([purpose, group]) => {
      // Newest first: the current state is the first thing to read.
      const history = [...group].sort((a, b) => Date.parse(b.at) - Date.parse(a.at));
      const latest = history[0];
      return {
        purpose,
        wording: latest.wording,
        granted: latest.granted,
        changed: ago(latest.at, now),
        changes: history.length,
        history,
        action: latest.granted ? ('withdraw' as const) : ('allow' as const),
      };
    })
    .sort((a, b) => Number(b.granted) - Number(a.granted) || a.purpose.localeCompare(b.purpose));

  const allowed = rows.filter((row) => row.granted).length;

  return {
    rows,
    summary:
      rows.length === 0 ? 'Nothing has been asked of you yet' : `${allowed} of ${rows.length} allowed`,
  };
}

function ago(at: string, now: Date): string {
  const days = Math.round((now.getTime() - Date.parse(at)) / DAY);
  if (days < 1) return 'today';
  return `${days} day${days === 1 ? '' : 's'} ago`;
}
