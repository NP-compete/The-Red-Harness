export interface FeatureFact {
  key: string;
  enabled: boolean;
  scope: 'deployment' | 'agent' | 'user';
  decided_by: string;
  overruled: boolean;
  missing: string[];
  cost: string;
}

export interface PresentedFeature {
  key: string;
  /**
   * Four states, not two.
   *
   * `off` is nobody has turned it on. `blocked` is somebody tried
   * and a wider scope refused. `unavailable` is it is waiting on
   * something else. Collapsing those three into "off" is how a
   * switch ends up doing nothing with no explanation.
   */
  state: 'on' | 'off' | 'blocked' | 'unavailable';
  changeable: boolean;
  decidedBy: string;
  blockedBy?: string;
  needs: string[];
  cost: string;
}

export function presentFeature(fact: FeatureFact): PresentedFeature {
  const waiting = fact.missing.length > 0;
  const refused = fact.overruled && !fact.enabled;

  let state: PresentedFeature['state'] = fact.enabled ? 'on' : 'off';
  if (waiting) state = 'unavailable';
  else if (refused) state = 'blocked';

  return {
    key: fact.key,
    state,
    // Offering a switch that cannot move is worse than offering none.
    changeable: !waiting && !refused,
    decidedBy: fact.decided_by,
    blockedBy: refused ? fact.decided_by : undefined,
    needs: fact.missing,
    cost: fact.cost,
  };
}
