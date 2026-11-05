export interface SandboxPlan {
  permitted: boolean;
  seconds: number;
  memoryMb: number;
  network: boolean;
  writablePaths: string[];
  maxOutputBytes: number;
  reason: string;
}

export interface PresentedSandbox {
  limits: string;
  network: string;
  writable: string[];
  writableNote: string;
  warning: string;
  severity: 'low' | 'high';
  canRun: boolean;
}

export function presentSandbox(plan: SandboxPlan): PresentedSandbox {
  const places = plan.writablePaths.length;

  return {
    limits: plan.permitted
      ? `up to ${plan.seconds} seconds, ${plan.memoryMb} MB of memory`
      : plan.reason,
    network: plan.network ? 'can reach the network' : 'no network access',
    writable: plan.writablePaths,
    writableNote:
      places === 0
        ? 'cannot write any files'
        : `can write to ${places} place${places === 1 ? '' : 's'}`,
    // Reading files is only half a leak; the other half is a way out.
    warning:
      plan.network && places > 0
        ? 'This code can both read your files and send data out'
        : '',
    severity: plan.network ? 'high' : 'low',
    canRun: plan.permitted,
  };
}
