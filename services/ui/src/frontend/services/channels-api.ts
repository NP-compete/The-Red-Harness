import { buildAgentApiUrl } from '../lib/app-paths';
import { authenticatedFetch } from './authenticated-fetch';

export interface Channel {
  name: string;
  type: string;
  assistantId?: string;
}

/**
 * The channels this agent is reachable on.
 *
 * Names and types only — the agent deliberately publishes no secrets
 * or identity maps here, and neither does this.
 */
export async function listChannels(): Promise<Channel[]> {
  try {
    const response = await authenticatedFetch(buildAgentApiUrl('/channels/'), {
      method: 'GET',
    });
    if (!response.ok) return [];
    const body = (await response.json()) as { channels?: unknown };
    if (!Array.isArray(body.channels)) return [];
    return body.channels
      .filter(
        (channel): channel is { name: string; type?: string; assistant_id?: string } =>
          Boolean(channel && typeof channel === 'object' && 'name' in channel && channel.name),
      )
      .map((channel) => ({
        name: channel.name,
        type: channel.type ?? 'unknown',
        assistantId: channel.assistant_id,
      }));
  } catch {
    return [];
  }
}
