import { useTranslation } from 'react-i18next';

/**
 * The one way an unreachable integration is offered to the reader.
 *
 * There were two: an interrupt raised inside a subagent rendered a
 * blue pill button under a sentence about "external tools", while
 * the orchestrator's own failures rendered a small bordered button
 * inside an amber row naming the integration. Same event, two
 * designs, and the reader had no way to know they meant the same
 * thing. Both call this now, so they cannot drift again.
 *
 * Connecting does NOT happen here, and neither does navigating.
 *
 * It used to: the button opened an OAuth popup mid-conversation and
 * the turn resumed by itself when the popup closed. That put an
 * authentication flow — a popup, a redirect, a provider's consent
 * screen — in the middle of a reply, and then restarted the question
 * on an event the reader had not obviously asked for.
 *
 * The row is now a sentence and nothing else. A button here, even
 * one that only navigated, still reads as the next step in the
 * conversation; the reader presses it, lands somewhere else, and has
 * lost the question they were asking. Told in words where to go,
 * they go when they are ready and come back to a thread that is
 * where they left it.
 *
 * It has one state. Once the integration is connected there is
 * nothing here worth saying, so the caller stops rendering it rather
 * than swapping the sentence for another one.
 *
 * It takes a list, not a name. A turn that touches six unconnected
 * servers used to stack six identical boxes differing only in the
 * first word — six copies of "Connect it in Settings → Components →
 * MCP, then ask again" for one trip to one page. One sentence naming
 * all six says the same thing and reads as the single action it is.
 */
export interface McpConnectRowProps {
  /** One or more server names sharing the same reason. */
  mcpNames: string[];
  /** `not_connected` or `expired` — different sentences, different fixes. */
  reason?: string;
}

/** `dataverse` -> `Dataverse`, `unstructured-data` -> `Unstructured data`.
 *
 * The server name is an identifier; dropped straight into a sentence
 * it read as "dataverse is not connected."
 */
export function integrationLabel(name: string): string {
  const spaced = name.replace(/[-_]+/g, ' ').trim();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/** "Atlan, Datadog and Miro" — in the reader's own language. */
function joinNames(names: string[], locale?: string): string {
  const labelled = names.map(integrationLabel);
  if (labelled.length < 2) return labelled[0] ?? '';
  // `Intl.ListFormat` knows that Japanese does not use "and" and that
  // Spanish turns it into "e" before an i- sound. Hand-joining with a
  // comma got that wrong in four of the six locales shipped here.
  // `Intl.ListFormat` is ES2021 and this app's lib is ES2020, so it
  // is declared here rather than widening the lib for one call. The
  // runtime check is real: every browser we support has it, jsdom in
  // some versions does not.
  const intl = Intl as typeof Intl & {
    ListFormat?: new (
      locale?: string,
      options?: { style?: string; type?: string },
    ) => { format(items: string[]): string };
  };
  if (intl.ListFormat) {
    return new intl.ListFormat(locale, { style: 'long', type: 'conjunction' }).format(
      labelled,
    );
  }
  return labelled.join(', ');
}

export function McpConnectRow({ mcpNames, reason }: McpConnectRowProps) {
  const { t, i18n } = useTranslation();
  if (mcpNames.length === 0) return null;

  // Locale is optional for `ListFormat`, which falls back to the
  // runtime default — so an absent `i18n` is not worth crashing over.
  const names = joinNames(mcpNames, i18n?.language);
  const many = mcpNames.length > 1;
  const key = reason === 'expired'
    ? (many ? 'mcpAuth.expiredGoToSettingsMany' : 'mcpAuth.expiredGoToSettings')
    : (many ? 'mcpAuth.notConnectedGoToSettingsMany' : 'mcpAuth.notConnectedGoToSettings');

  return (
    <div
      className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm"
      data-testid={`mcp-connect-${mcpNames.join('-')}`}
    >
      {t(key, { name: names, names })}
    </div>
  );
}

export default McpConnectRow;
