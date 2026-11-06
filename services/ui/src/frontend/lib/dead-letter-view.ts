export interface DeadLetter {
  deliveryId: string;
  destination: string;
  reason: string;
  replayable: boolean;
  parkedAt: string;
}

export interface DeadLetterGroup {
  destination: string;
  count: number;
  reason: string;
  latest: string;
  note: string;
  action: 'replay' | 'discard';
}

export interface PresentedDeadLetters {
  groups: DeadLetterGroup[];
  total: number;
  replayable: number;
  emptyMessage: string;
}

export function presentDeadLetters(items: DeadLetter[], now: Date): PresentedDeadLetters {
  const byDestination = new Map<string, DeadLetter[]>();
  for (const item of items) {
    byDestination.set(item.destination, [...(byDestination.get(item.destination) ?? []), item]);
  }

  const groups = [...byDestination.entries()]
    .map(([destination, group]) => {
      const replayable = group.some((item) => item.replayable);
      return {
        destination,
        count: group.length,
        reason: commonest(group.map((item) => item.reason)),
        latest: ago(
          group.reduce((newest, item) => (item.parkedAt > newest ? item.parkedAt : newest), group[0].parkedAt),
          now,
        ),
        // Offering a replay that is certain to fail wastes the operator's time.
        note: replayable ? '' : 'Replaying this would be refused again',
        action: replayable ? ('replay' as const) : ('discard' as const),
      };
    })
    .sort((a, b) => b.count - a.count || a.destination.localeCompare(b.destination));

  return {
    groups,
    total: items.length,
    replayable: items.filter((item) => item.replayable).length,
    emptyMessage: items.length === 0 ? 'Nothing has failed delivery' : '',
  };
}

function commonest(values: string[]): string {
  const counts = new Map<string, number>();
  for (const value of values) counts.set(value, (counts.get(value) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0][0];
}

function ago(at: string, now: Date): string {
  const minutes = Math.round((now.getTime() - Date.parse(at)) / 60_000);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
  const hours = Math.round(minutes / 60);
  return `${hours} hour${hours === 1 ? '' : 's'} ago`;
}
