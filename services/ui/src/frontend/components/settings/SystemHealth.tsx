import { useEffect, useState } from 'react';

import { presentSystemHealth, type SystemStatus } from '../../lib/system-health';
import { getSystemHealth } from '../../services/system-health';

/**
 * Which parts the agent depends on, and whether each is answering.
 *
 * The header says whether the agent is up; it cannot say which piece
 * is down when it is not, which is the first thing an operator asks.
 */
export function SystemHealth() {
  const [systems, setSystems] = useState<SystemStatus[] | null>(null);

  useEffect(() => {
    let alive = true;
    void getSystemHealth().then((found) => {
      if (alive) setSystems(found);
    });
    return () => {
      alive = false;
    };
  }, []);

  if (!systems) {
    return null;
  }

  const health = presentSystemHealth(systems);

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">{health.summary}</p>
      <ul className="list-none space-y-1">
        {health.rows.map((row) => (
          <li
            key={row.name}
            className="flex items-baseline justify-between gap-3 rounded-lg border border-border bg-card px-3 py-2"
          >
            <code className="text-sm text-foreground">{row.name}</code>
            {/* The presenter also works out an action per row — connect,
                retry — which belongs to a server somebody chose to add.
                Nobody connects a checkpointer by hand, so the state is
                reported and nothing is offered. */}
            <span
              className={
                row.status === 'Connected'
                  ? 'text-xs text-muted-foreground'
                  : 'text-xs text-amber-600 dark:text-amber-500'
              }
            >
              {row.status}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
