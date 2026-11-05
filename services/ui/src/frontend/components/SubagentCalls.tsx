import { useTranslation } from 'react-i18next';
import { useEffect, useState } from 'react';
import { ChevronRight } from 'lucide-react';

import { getSubagentCalls, type SubagentCall } from '../services/subagent-calls';

function describe(args: Record<string, unknown>): string {
  const first = Object.values(args).find((value) => typeof value === 'string');
  return typeof first === 'string' ? first : JSON.stringify(args);
}

/**
 * What the delegated steps of this conversation actually ran.
 *
 * A subagent reports as one line and a duration, which says how long
 * it took and nothing about whether it looked in the right place.
 */
export function SubagentCalls({ threadId }: { threadId: string }) {
  const { t } = useTranslation();
  const [calls, setCalls] = useState<SubagentCall[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!threadId) return;
    let alive = true;
    void getSubagentCalls(threadId).then((found) => {
      if (alive) setCalls(found);
    });
    return () => {
      alive = false;
    };
  }, [threadId]);

  // Nothing ran, or this reader may not see it. Neither is worth a line.
  if (calls.length === 0) {
    return null;
  }

  return (
    <div className="pl-11 mt-1 text-[11px]">
      <button
        type="button"
        onClick={() => setOpen((was) => !was)}
        className="inline-flex items-center gap-1 text-muted-foreground transition-colors hover:text-foreground"
      >
        <ChevronRight
          className={`h-3 w-3 transition-transform ${open ? 'rotate-90' : ''}`}
          aria-hidden="true"
        />
        {t('counts.delegated', { count: calls.length })}
      </button>
      {open && (
        <ul className="mt-1 list-none space-y-1 border-l border-border pl-3">
          {calls.map((call, index) => (
            <li key={`${call.name}-${index}`} className="text-muted-foreground">
              <code className="text-foreground">{call.name}</code>
              <span className="ml-2 line-clamp-2 break-all">{describe(call.args)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
