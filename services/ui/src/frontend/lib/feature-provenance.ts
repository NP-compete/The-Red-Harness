export interface FeatureFlag {
  key: string;
  scope: 'deployment' | 'agent' | 'user';
  /** What changes when it is on. */
  effect: string;
  value: boolean;
  source: 'default' | 'configuration file' | 'environment' | 'set here';
  /** The environment variable that decided it, when one did. */
  setBy?: string;
  overridable: boolean;
}

export interface FlagChange {
  key: string;
  from: boolean | null;
  to: boolean;
  who: string;
  when: string;
}

/**
 * Which level decided a flag, in a few words.
 *
 * A switch that is absent because something wider already settled
 * the question looks like an oversight unless the page says so.
 */
export function whereFrom(flag: FeatureFlag): string {
  if (flag.source === 'environment') {
    return flag.setBy
      ? `Set outside this deployment, by ${flag.setBy}`
      : 'Set outside this deployment';
  }
  if (flag.source === 'configuration file') return 'Set in the configuration file';
  if (flag.source === 'set here') return 'Set here';
  return 'Left at its default';
}
