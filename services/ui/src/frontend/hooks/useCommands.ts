import { useEffect, useState } from 'react';

import { buildAppPath } from '../lib/app-paths';
import type { PaletteCommand } from '../lib/command-palette';

/** The commands the agent offers, or none if it cannot be asked. */
export function useCommands(): PaletteCommand[] {
  const [commands, setCommands] = useState<PaletteCommand[]>([]);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const res = await fetch(buildAppPath('/api/proxy/agent/commands'), {
          credentials: 'same-origin',
          signal: AbortSignal.timeout(10_000),
        });
        if (!res.ok) return;
        const body = (await res.json()) as { commands?: PaletteCommand[] };
        if (alive && Array.isArray(body.commands)) setCommands(body.commands);
      } catch {
        // Offering no commands is better than offering ones that fail.
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  return commands;
}
