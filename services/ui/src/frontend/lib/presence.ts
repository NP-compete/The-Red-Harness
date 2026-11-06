export interface PresenceInput {
  me: string;
  viewers: string[];
  holder?: string;
}

export interface PresentedPresence {
  others: string[];
  summary: string;
  canSend: boolean;
  action?: 'request-handover';
}

export function presentPresence({ me, viewers, holder }: PresenceInput): PresentedPresence {
  const others = [...new Set(viewers.filter((viewer) => viewer !== me))];
  const heldByOther = holder !== undefined && holder !== me;

  return {
    others,
    summary: summarise(me, others, holder),
    canSend: !heldByOther,
    action: heldByOther ? 'request-handover' : undefined,
  };
}

function summarise(me: string, others: string[], holder?: string): string {
  if (holder === me) return 'You are running this';
  if (holder !== undefined) return `${holder} is running this`;
  return others.length === 0 ? 'Only you' : `With ${others.join(', ')}`;
}
