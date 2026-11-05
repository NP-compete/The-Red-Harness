export interface AssistantUsage {
  assistant: string;
  runs: number;
  errors: number;
  threads: number;
  p95_seconds: number | null;
}

export interface AssistantRow extends AssistantUsage {
  /** What to show in the column. */
  label: string;
  /** Null when nothing ran: no runs means no rate. */
  errorRate: number | null;
  p95: number | null;
}

// Enough of a uuid to tell two apart at a glance, short enough to
// leave room for the figures the table exists for.
const SHORT = 12;

/**
 * The per-assistant table, in the order somebody reads it.
 *
 * Busiest first: the assistant being asked about is almost always
 * the one doing the most.
 */
export function assistantRows(rows: AssistantUsage[]): AssistantRow[] {
  return [...rows]
    .sort((a, b) => b.runs - a.runs)
    .map((row) => ({
      ...row,
      label: shorten(row.assistant),
      // Null, not zero. Zero per cent is a claim that everything
      // worked, and nothing running is not that claim.
      errorRate: row.runs > 0 ? row.errors / row.runs : null,
      p95: row.p95_seconds,
    }));
}

/**
 * An identifier, trimmed to something a column can hold.
 *
 * Only when it looks like one: a configured name is already what
 * somebody meant to read, and cutting it would hide the useful
 * half.
 */
function shorten(assistant: string): string {
  if (assistant.length <= SHORT) return assistant;
  return `${assistant.slice(0, SHORT)}…`;
}
