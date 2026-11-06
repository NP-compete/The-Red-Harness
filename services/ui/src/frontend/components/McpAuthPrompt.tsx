import { useEffect, useState } from 'react';
import { type McpAuthRequest } from '../lib/mcp-auth-marker';
import { McpConnectRow } from './McpConnectRow';
import { verifyMcpOAuthConnected } from '../services/mcp-oauth-api';

interface Props {
  requests: McpAuthRequest[];
}

/**
 * Inline notice that an integration this turn needed is not connected.
 *
 * It does not connect anything. The OAuth popup, the close-watcher
 * that polled it, and the callback that resumed the question all
 * lived here; connecting now happens on the settings page and the
 * reader asks again afterwards. What is left is the part that keeps
 * the notice honest.
 */
export function McpAuthPrompt({ requests }: Props) {
  const [connected, setConnected] = useState<string[]>([]);

  // Re-check on mount and whenever the tab regains focus.
  //
  // The prompt is pinned to a message, and a message does not
  // change. Connect from the settings page, from another tab, or
  // reload after connecting, and this banner went on insisting the
  // integration was not connected — contradicting the settings page
  // and the next answer, on a turn the user had already fixed. The
  // request list says what was true when the turn ran; whether it is
  // still true is a question only the server can answer.
  //
  // A row that is no longer true is removed, not reworded. The
  // sentence it would be replaced with has nothing in it the reader
  // does not already know.
  const names = requests.map((r) => r.mcpName).join(',');
  useEffect(() => {
    if (names === '') return;
    let cancelled = false;

    const recheck = async () => {
      const checked = await Promise.all(
        names.split(',').map(async (name) => [name, await verifyMcpOAuthConnected(name)] as const),
      );
      if (cancelled) return;
      setConnected(checked.filter(([, ok]) => ok).map(([name]) => name));
    };

    void recheck();
    const onFocus = () => void recheck();
    window.addEventListener('focus', onFocus);
    return () => {
      cancelled = true;
      window.removeEventListener('focus', onFocus);
    };
  }, [names]);

  const outstanding = requests.filter((r) => !connected.includes(r.mcpName));
  if (outstanding.length === 0) return null;

  // Grouped by reason, not one box per server. Six unconnected
  // integrations produced six boxes that differed only in their first
  // word, each repeating the same instruction to visit the same page.
  // Not connected and expired stay apart because they are different
  // fixes; within each, one sentence names them all.
  const byReason = new Map<string, string[]>();
  for (const req of outstanding) {
    const reason = req.reason === 'expired' ? 'expired' : 'not_connected';
    byReason.set(reason, [...(byReason.get(reason) ?? []), req.mcpName]);
  }

  return (
    <div className="mt-2 flex flex-col gap-2" data-testid="mcp-auth-prompt">
      {[...byReason].map(([reason, names]) => (
        <McpConnectRow key={reason} mcpNames={names} reason={reason} />
      ))}
    </div>
  );
}

export default McpAuthPrompt;
