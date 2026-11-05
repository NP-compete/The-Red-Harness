/**
 * Whether a server's own credential is there.
 *
 * A server set to use an API key whose key is absent looks
 * exactly like one that works: the dot is green because the
 * server is enabled, and nothing says the next call will fail
 * until somebody makes one.
 *
 * Said only when it is wrong. A deployment with thirteen
 * servers configured correctly does not need thirteen rows
 * each confirming it, and a line that appears on every row is
 * one nobody reads on the row that mattered.
 *
 * Presence only. The agent reports three words and never the
 * key, nor the variable holding it.
 */

export type CredentialState = 'set' | 'missing' | 'not needed';

export function credentialWarning(server: {
  enabled: boolean;
  credential?: CredentialState | string;
}): string | null {
  // A server that is off reaches nothing, so its credential
  // cannot matter. Warning anyway is noise on every
  // deliberately-disabled row.
  if (!server.enabled) return null;
  if (server.credential !== 'missing') return null;

  return 'This server signs in with its own key, and the key is not set.';
}
