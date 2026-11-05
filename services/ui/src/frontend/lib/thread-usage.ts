export interface ThreadUsage {
  used: number;
  inputTokens: number;
  outputTokens: number;
  cacheRead: number;
  /** What it came to in money, when a price list priced it. */
  cost?: string | null;
  currency?: string;
}

/**
 * What a conversation has used, added up from the answers themselves.
 *
 * Every reply carries its own count, so this needs nothing kept on the
 * side and is right for exactly the turns on screen.
 */
export function sumUsage(messages: unknown[]): ThreadUsage | null {
  const total: ThreadUsage = { used: 0, inputTokens: 0, outputTokens: 0, cacheRead: 0 };
  let counted = false;

  for (const message of messages) {
    const usage = (message as { usage_metadata?: Record<string, unknown> })?.usage_metadata;
    if (!usage || typeof usage !== 'object') continue;

    const input = number(usage.input_tokens);
    const output = number(usage.output_tokens);
    const stated = number(usage.total_tokens);
    const details = usage.input_token_details as Record<string, unknown> | undefined;

    counted = true;
    total.inputTokens += input;
    total.outputTokens += output;
    total.used += stated || input + output;
    total.cacheRead += number(details?.cache_read);
  }

  return counted ? total : null;
}

function number(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}
