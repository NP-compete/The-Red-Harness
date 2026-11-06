export interface BrowserSays {
  /** `navigator.userAgentData.platform`, where the browser has it. */
  platform?: string;
  userAgent?: string;
}

/**
 * Whether a desktop notification is worth asking permission for.
 *
 * Unknown counts as unsupported, and that asymmetry is deliberate.
 * Offering nothing on a platform that would have worked is a missing
 * feature somebody can report. Prompting for permission where
 * delivery is unreliable teaches people the prompt is noise — and
 * they refuse the next one too, including the one that mattered.
 *
 * The allowlist is configuration rather than a constant here, so a
 * deployment that wants another platform can have it without a code
 * change, and so the decision is visible rather than buried.
 */
export function notifiable(says: BrowserSays, allowed: string[]): boolean {
  const found = says.platform?.trim() || guess(says.userAgent ?? '');
  if (!found) return false;
  return allowed.includes(found);
}

/**
 * The vocabulary, not prose.
 *
 * These are matched against `navigator.userAgentData.platform` and
 * against the deployment's allowlist, so they are identifiers with
 * fixed spellings. Translating one would stop it matching.
 *
 * Ordered, and the order is the rule: each mobile platform names a
 * desktop in its own user-agent string — iPadOS says "Macintosh",
 * Android says "Linux" — so they are recognised first. Matching the
 * desktop names earlier would call a phone a workstation.
 */
const SIGNATURES: readonly (readonly [RegExp, string])[] = [
  [/Android/i, 'Android'],
  [/iPhone|iPad|iPod/i, 'iOS'],
  // iPadOS reports a desktop Safari string and gives itself away
  // only with "Mobile". Mapped to nothing: it is a platform this
  // cannot name, which is treated as unsupported.
  [/Mobile/i, ''],
  [/CrOS/i, 'Chrome OS'],
  [/Macintosh|Mac OS X/i, 'macOS'],
  [/Windows/i, 'Windows'],
  [/Linux|X11/i, 'Linux'],
];

/** The platform a user-agent string suggests, or nothing. */
function guess(userAgent: string): string {
  if (!userAgent) return '';
  for (const [pattern, name] of SIGNATURES) {
    if (pattern.test(userAgent)) return name;
  }
  return '';
}
