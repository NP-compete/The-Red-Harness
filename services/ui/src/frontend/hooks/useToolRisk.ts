import { useCallback, useEffect, useState } from 'react';

import { buildAppPath } from '../lib/app-paths';

interface ToolPolicy {
  decision?: string;
  risk?: string;
  reason?: string;
}

export interface ToolRisk {
  /** Whether the approval policy could be read at all. */
  known: boolean;
  isReversible: (tool: string) => boolean;
  riskOf: (tool: string) => string;
}

/**
 * What the approval policy says about each tool.
 *
 * A tool the policy stops for is one whose effects someone wanted a
 * person to see first, which is the closest thing the browser has to
 * "this cannot simply be undone". Anything unknown is assumed to be
 * the kinder case: a warning nobody can act on is worse than silence.
 */
export function useToolRisk(): ToolRisk {
  const [policies, setPolicies] = useState<Record<string, ToolPolicy> | null>(null);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const res = await fetch(buildAppPath('/api/proxy/agent/admin/config'), {
          credentials: 'same-origin',
          signal: AbortSignal.timeout(10_000),
        });
        if (!res.ok) return;
        const body = (await res.json()) as { approval?: { tools?: unknown } };
        const tools = body?.approval && typeof body.approval === 'object'
          ? (body.approval as { tools?: unknown }).tools
          : undefined;
        if (alive && tools && typeof tools === 'object') {
          setPolicies(tools as Record<string, ToolPolicy>);
        }
      } catch {
        // Not every reader may see the policy, and that is not a failure.
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const isReversible = useCallback(
    (tool: string) => {
      const decision = policies?.[tool]?.decision;
      return decision === undefined || decision === 'allow';
    },
    [policies],
  );

  const riskOf = useCallback((tool: string) => policies?.[tool]?.risk ?? '', [policies]);

  return { known: policies !== null, isReversible, riskOf };
}
