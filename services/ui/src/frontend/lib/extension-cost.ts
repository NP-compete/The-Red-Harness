export interface ExtensionTiming {
  calls: number;
  refusals: number;
  refusal_rate: number;
  average_ms: number;
  slowest_ms: number;
}

/**
 * What an extension has cost, in one line.
 *
 * An extension sits on every turn, so one that takes two seconds is
 * the whole agent taking two seconds longer. The average alone is
 * not enough: an extension that is usually quick and occasionally
 * very slow reads as fine until somebody hits the slow call.
 */
export function extensionCost(timing: ExtensionTiming | null | undefined): string {
  if (!timing) return '';

  const usual = Math.round(timing.average_ms);
  const worst = Math.round(timing.slowest_ms);

  const said = [`${usual} ms typical`];
  if (worst > usual) said.push(`${worst} ms slowest`);
  said.push(`${timing.calls} ${timing.calls === 1 ? 'call' : 'calls'}`);
  if (timing.refusals > 0) {
    said.push(`refused ${Math.round(timing.refusal_rate * 100)}% of the time`);
  }

  return said.join(' · ');
}
