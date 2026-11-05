/**
 * Facts about a conversation that only the agent knows.
 *
 * A conversation the browser has seen before is carried forward from
 * local storage, and only the ones new to this browser were given
 * what the agent says about them — so a thread already in the list
 * never learned that its run had died, or that it was a fork.
 */
interface ServerFacts {
  id: string;
  serverStatus?: string | null;
  forkedFrom?: string | null;
  forkedAt?: number | null;
}

export function refreshFromServer<T extends { id: string }>(
  known: T,
  fromServer: ServerFacts | undefined,
): T {
  if (!fromServer) return known;

  const refreshed = { ...known };
  if (fromServer.serverStatus !== undefined) {
    (refreshed as { serverStatus?: string | null }).serverStatus = fromServer.serverStatus;
  }
  if (fromServer.forkedFrom !== undefined) {
    (refreshed as { forkedFrom?: string | null }).forkedFrom = fromServer.forkedFrom;
  }
  if (fromServer.forkedAt !== undefined) {
    (refreshed as { forkedAt?: number | null }).forkedAt = fromServer.forkedAt;
  }
  return refreshed;
}
