export type SystemState = 'connected' | 'not-connected' | 'degraded';
export type SystemAction = 'connect' | 'retry' | 'disconnect';

export interface SystemStatus {
  name: string;
  state: SystemState;
  retryInSeconds?: number;
}

export interface SystemRow {
  name: string;
  status: string;
  action: SystemAction;
}

export interface PresentedHealth {
  rows: SystemRow[];
  summary: string;
}

const ACTIONS: Record<SystemState, SystemAction> = {
  connected: 'disconnect',
  'not-connected': 'connect',
  degraded: 'retry',
};

// Failing first, then waiting on the person, then everything that works.
const ORDER: Record<SystemState, number> = { degraded: 0, 'not-connected': 1, connected: 2 };

export function presentSystemHealth(systems: SystemStatus[]): PresentedHealth {
  const rows = [...systems]
    .sort((a, b) => ORDER[a.state] - ORDER[b.state] || a.name.localeCompare(b.name))
    .map<SystemRow>((system) => ({
      name: system.name,
      status: describe(system),
      action: ACTIONS[system.state],
    }));

  return { rows, summary: summarise(systems) };
}

function describe(system: SystemStatus): string {
  if (system.state === 'connected') return 'Connected';
  if (system.state === 'not-connected') return 'Not connected';
  return system.retryInSeconds === undefined
    ? 'Unavailable'
    : `Unavailable, retrying in ${system.retryInSeconds}s`;
}

function summarise(systems: SystemStatus[]): string {
  if (systems.length === 0) return 'Nothing connected yet';

  const counts = {
    connected: systems.filter((s) => s.state === 'connected').length,
    attention: systems.filter((s) => s.state === 'not-connected').length,
    failing: systems.filter((s) => s.state === 'degraded').length,
  };

  const parts = [`${counts.connected} connected`];
  if (counts.attention > 0) parts.push(`${counts.attention} needs attention`);
  if (counts.failing > 0) parts.push(`${counts.failing} failing`);
  return parts.join(', ');
}
