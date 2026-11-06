export interface Delivery {
  at: string;
  outcome: 'ok' | 'failed';
}

export interface Trigger {
  id: string;
  source: string;
  eventType: string;
  agent: string;
  paused: boolean;
  verified: boolean;
  lastDelivery: Delivery | null;
  deliveriesToday: number;
}

export interface PresentedTrigger {
  id: string;
  summary: string;
  state: 'active' | 'paused';
  lastDelivery: string;
  volume: string;
  warning: string;
  healthy: boolean;
}

export function presentTriggers(triggers: Trigger[], now: Date): PresentedTrigger[] {
  return triggers
    .map((trigger) => present(trigger, now))
    .sort((a, b) => Number(a.healthy) - Number(b.healthy));
}

function present(trigger: Trigger, now: Date): PresentedTrigger {
  const neverFired = trigger.lastDelivery === null;
  const failed = trigger.lastDelivery?.outcome === 'failed';

  return {
    id: trigger.id,
    summary: `${trigger.eventType} from ${trigger.source} starts ${trigger.agent}`,
    state: trigger.paused ? 'paused' : 'active',
    lastDelivery: trigger.lastDelivery ? describeAgo(trigger.lastDelivery.at, now) : 'nothing yet',
    volume: `${trigger.deliveriesToday} runs today`,
    warning: trigger.verified ? '' : 'This source is not verified, so anyone could send it.',
    // A paused trigger is silent on purpose; silence elsewhere is a fault.
    healthy: trigger.verified && (trigger.paused || (!neverFired && !failed)),
  };
}

function describeAgo(at: string, now: Date): string {
  const hours = Math.round((now.getTime() - new Date(at).getTime()) / 3_600_000);
  if (hours < 1) return 'just now';
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}
