export type Scope = 'deployment' | 'agent' | 'user';

export interface Requirement {
  name: string;
  met: boolean;
}

export interface CapabilityInput {
  name: string;
  deployment?: boolean;
  agent?: boolean;
  user?: boolean;
  requires?: Requirement[];
  cost?: string;
}

export interface ResolvedCapability {
  name: string;
  enabled: boolean;
  decidedBy: Scope;
  togglable: boolean;
  blockedBy: string[];
  cost?: string;
}

export function resolveCapability(input: CapabilityInput): ResolvedCapability {
  const blockedBy = (input.requires ?? []).filter((r) => !r.met).map((r) => r.name);

  const levels: Array<[Scope, boolean | undefined]> = [
    ['deployment', input.deployment],
    ['agent', input.agent],
    ['user', input.user],
  ];

  // Each level may narrow what the one above allows, never widen it.
  let enabled = false;
  let decidedBy: Scope = 'deployment';
  for (const [scope, value] of levels) {
    if (value === undefined) continue;
    if (scope === 'deployment') {
      enabled = value;
      decidedBy = scope;
      continue;
    }
    if (enabled && !value) {
      enabled = false;
      decidedBy = scope;
    }
  }

  return {
    name: input.name,
    enabled: enabled && blockedBy.length === 0,
    decidedBy,
    togglable: blockedBy.length === 0,
    blockedBy,
    cost: input.cost,
  };
}
