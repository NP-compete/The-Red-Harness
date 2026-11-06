export interface RequestState {
  kind: 'export' | 'delete';
  included: string[];
  withheld: Record<string, string>;
  complete: boolean;
  dueAt: string;
  notice: string;
  state: 'planned' | 'running' | 'done';
}

export interface Exception {
  place: string;
  reason: string;
}

export interface PresentedRequest {
  headline: string;
  covered: string[];
  exceptions: Exception[];
  warning: string;
  due: string;
  severity: 'info' | 'medium' | 'high';
  confirmFirst: boolean;
}

const DAY = 86_400_000;

export function presentRequest(request: RequestState, now: Date): PresentedRequest {
  const done = request.state === 'done';
  const overdue = !done && Date.parse(request.dueAt) <= now.getTime();

  return {
    headline: `Request to ${request.kind} your data`,
    covered: request.included,
    exceptions: Object.entries(request.withheld)
      .map(([place, reason]) => ({ place, reason }))
      .sort((a, b) => a.place.localeCompare(b.place)),
    warning: request.notice,
    due: done ? 'completed' : overdue ? 'overdue' : `due in ${days(request.dueAt, now)} days`,
    severity: overdue ? 'high' : request.complete ? 'info' : 'medium',
    // Deleting is the irreversible one; exporting can be repeated.
    confirmFirst: !done && request.kind === 'delete',
  };
}

function days(at: string, now: Date): number {
  return Math.round((Date.parse(at) - now.getTime()) / DAY);
}
