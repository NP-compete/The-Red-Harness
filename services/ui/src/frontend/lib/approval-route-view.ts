export interface RouteDecision {
  approvers: string[];
  waitMinutes: number;
  escalateTo: string;
  onTimeout: 'proceed' | 'refuse';
  askNow: boolean;
  nobodyToAsk: boolean;
  reason: string;
}

export interface PresentedRoute {
  headline: string;
  asking: string;
  deadline: string;
  escalation: string;
  ifNobodyAnswers: string;
  state: string;
  severity: 'info' | 'medium' | 'high';
  action: 'choose-approver';
}

export function presentRoute(route: RouteDecision): PresentedRoute {
  const proceeds = route.onTimeout === 'proceed';

  return {
    headline: route.reason,
    asking: route.nobodyToAsk
      ? 'There is nobody who can approve this'
      : `Asking ${list(route.approvers)}`,
    deadline: `${route.waitMinutes} minutes to answer`,
    escalation: route.escalateTo ? `Then ${route.escalateTo}` : 'Nobody after them',
    // What silence means is the part people assume wrongly, so it is stated.
    ifNobodyAnswers: proceeds
      ? 'If nobody answers, this will go ahead'
      : 'If nobody answers, this will not happen',
    state: route.askNow ? 'asked' : 'waiting to be asked',
    severity: route.nobodyToAsk ? 'high' : proceeds ? 'medium' : 'info',
    action: 'choose-approver',
  };
}

function list(names: string[]): string {
  if (names.length <= 1) return names[0] ?? '';
  return `${names.slice(0, -1).join(', ')} or ${names[names.length - 1]}`;
}
