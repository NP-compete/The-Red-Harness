export type Trigger = 'schedule' | 'event' | 'call' | 'manual';
export type AgentState = 'healthy' | 'waiting' | 'stuck';
export type HeadlessAction = 'approve' | 'refuse' | 'stop';

export interface HeadlessAgent {
  name: string;
  trigger: Trigger;
  actsAs: string;
  state: AgentState;
  schedule?: string;
  lastRun?: string;
}

export interface HeadlessRow {
  name: string;
  when: string;
  actsAs: string;
  state: AgentState;
  lastRun?: string;
  needsAttention: boolean;
  actions: HeadlessAction[];
}

export interface PresentedHeadless {
  rows: HeadlessRow[];
  needingAttention: number;
}

const WHEN: Record<Trigger, string> = {
  schedule: 'on a schedule',
  event: 'on an event',
  call: 'when another system calls',
  manual: 'when somebody runs it',
};

const ACTIONS: Record<AgentState, HeadlessAction[]> = {
  healthy: [],
  waiting: ['approve', 'refuse'],
  stuck: ['stop'],
};

export function presentHeadless(agents: HeadlessAgent[]): PresentedHeadless {
  const rows = agents
    .map<HeadlessRow>((agent) => ({
      name: agent.name,
      when: agent.schedule ?? WHEN[agent.trigger],
      actsAs: agent.actsAs,
      state: agent.state,
      lastRun: agent.lastRun,
      needsAttention: agent.state !== 'healthy',
      actions: ACTIONS[agent.state],
    }))
    // Whatever is blocked or broken is what somebody opened this for.
    .sort((a, b) => Number(b.needsAttention) - Number(a.needsAttention));

  return { rows, needingAttention: rows.filter((row) => row.needsAttention).length };
}
