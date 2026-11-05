/**
 * Put the shell worker in place, if this deployment wants one.
 *
 * An enhancement, never a dependency. The application works without
 * a worker, so every way this can fail returns nothing rather than
 * throwing — a rejected registration must not be the reason a page
 * does not load.
 */
export async function registerShellWorker({
  enabled,
  nav = typeof navigator === 'undefined' ? undefined : navigator,
}: {
  enabled: boolean;
  nav?: Navigator;
}): Promise<ServiceWorkerRegistration | null> {
  if (!enabled) return null;
  const container = (nav as { serviceWorker?: ServiceWorkerContainer } | undefined)
    ?.serviceWorker;
  if (!container) return null;

  try {
    // Scoped to the whole application, which is what makes an
    // offline navigation to any route resolve to the shell.
    return await container.register('/sw.js', { scope: '/' });
  } catch {
    return null;
  }
}
