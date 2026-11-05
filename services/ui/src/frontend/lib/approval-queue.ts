export interface PendingApproval {
  id: string;
  tool: string;
  summary: string;
  requestedBy: string;
  requestedAt: string;
  expiresAt: string;
  eligibleApprovers: string[];
  requesterId: string;
}

export interface Viewer {
  now: Date;
  viewerId: string;
}

export interface PresentedApproval {
  id: string;
  title: string;
  requestedBy: string;
  timeLeft: string;
  urgent: boolean;
  canAct: boolean;
  canWithdraw: boolean;
  blockedReason: string;
}

const URGENT_SECONDS = 300;

export function presentApprovalQueue(
  pending: PendingApproval[],
  viewer: Viewer,
): PresentedApproval[] {
  return pending
    .map((item) => present(item, viewer))
    .sort((a, b) => a.secondsLeft - b.secondsLeft)
    .map(({ secondsLeft: _secondsLeft, ...shown }) => shown);
}

function present(
  item: PendingApproval,
  { now, viewerId }: Viewer,
): PresentedApproval & { secondsLeft: number } {
  const secondsLeft = (new Date(item.expiresAt).getTime() - now.getTime()) / 1000;
  const expired = secondsLeft <= 0;
  const isRequester = viewerId === item.requesterId;
  const eligible = item.eligibleApprovers.includes(viewerId);

  return {
    id: item.id,
    title: item.summary,
    requestedBy: item.requestedBy,
    timeLeft: expired ? 'expired' : `${Math.round(secondsLeft / 60)} minutes left`,
    urgent: !expired && secondsLeft <= URGENT_SECONDS,
    canAct: !expired && eligible && !isRequester,
    // Withdrawal is not approval, so the requester keeps it.
    canWithdraw: !expired && isRequester,
    blockedReason: blockedReason({ expired, isRequester, eligible, item }),
    secondsLeft: expired ? Infinity : secondsLeft,
  };
}

function blockedReason({
  expired,
  isRequester,
  eligible,
  item,
}: {
  expired: boolean;
  isRequester: boolean;
  eligible: boolean;
  item: PendingApproval;
}): string {
  if (expired) return 'Nobody answered in time, so this did not go ahead.';
  if (isRequester) return 'You cannot approve your own request.';
  if (eligible) return '';
  return `Waiting on ${joinNames(item.eligibleApprovers)}.`;
}

function joinNames(names: string[]): string {
  if (names.length === 0) return 'nobody';
  if (names.length === 1) return names[0];
  return `${names.slice(0, -1).join(', ')} or ${names[names.length - 1]}`;
}
