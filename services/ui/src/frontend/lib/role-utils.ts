const PRIVILEGED_ROLES = new Set(["owners", "admins", "builders"]);

/**
 * Whether to show the operator surfaces: developer mode, evals, usage.
 *
 * A declared role answers it. With sign-in switched off there is no
 * role to read and nobody to tell apart, so hiding those surfaces
 * hides them from everyone — including whoever is running this
 * locally. The agent enforces its own authorization either way.
 */
export function isPrivilegedUser(): boolean {
  const role = window.APP_DATA?.userRole;
  if (role != null) return PRIVILEGED_ROLES.has(role);

  // The agent decides this for itself, so its answer beats anything
  // worked out from the settings — and it is the same answer it will
  // enforce when the page asks for an operator surface.
  if (agentRole != null) return PRIVILEGED_ROLES.has(agentRole);

  const embedded = window.APP_DATA?.features?.auth_enabled;
  const known = embedded ?? loadedAuthEnabled;
  return known === false;
}

/**
 * Whether the answer above can be given yet.
 *
 * With sign-in off the flag arrives with the configuration, a moment
 * after the first render. Deciding in that moment sends an allowed
 * reader away from a page they can open.
 */
export function privilegeKnown(): boolean {
  return (
    window.APP_DATA?.userRole != null ||
    agentRole != null ||
    window.APP_DATA?.features?.auth_enabled !== undefined ||
    loadedAuthEnabled !== undefined
  );
}

let loadedAuthEnabled: boolean | undefined;
let agentRole: string | undefined;
const listeners = new Set<() => void>();

/** Called back when the answer above becomes knowable. */
export function onPrivilegeKnown(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * Record whether sign-in is on, once the configuration has loaded.
 *
 * The flag arrives after the page was served, so it is not in the
 * data embedded in the HTML that this function can otherwise read.
 */
export function rememberAuthEnabled(enabled: boolean | undefined): void {
  loadedAuthEnabled = enabled;
  for (const listener of listeners) listener();
}

/**
 * Record the role the agent reports for this caller.
 *
 * Without it the page infers who it is talking to from whether
 * sign-in is switched on, which is a guess, and a guess that says yes
 * to everyone in a local deployment.
 */
export function rememberAgentRole(role: string | undefined): void {
  agentRole = role;
  for (const listener of listeners) listener();
}
