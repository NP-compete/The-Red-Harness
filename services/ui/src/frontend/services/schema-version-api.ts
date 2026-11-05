import { buildAppPath } from '../lib/app-paths';
import type { InboundReport } from '../lib/inbound-view';
import type { SchemaWindow } from '../lib/schema-view';

async function adminConfig(): Promise<Record<string, unknown> | null> {
  try {
    const response = await fetch(buildAppPath('/api/proxy/agent/admin/config'), {
      credentials: 'include',
    });
    if (!response.ok) return null;
    return (await response.json()) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/**
 * Whether another system may call this agent, and on what terms.
 *
 * `null` on anything other than a clean answer — an older agent
 * that has never been asked this is not a deployment with its door
 * open.
 */
export async function readInbound(): Promise<InboundReport | null> {
  const body = await adminConfig();
  const inbound = body?.inbound as InboundReport | undefined;
  return inbound && typeof inbound.enabled === 'boolean' ? inbound : null;
}

/**
 * The configuration layout a running pod accepts, and the one it was given.
 *
 * `null` on anything other than a clean answer. An older agent that
 * has never been asked this is not a deployment with no version, and
 * showing one would be worse than showing nothing.
 */
export async function readSchemaWindow(): Promise<SchemaWindow | null> {
  const body = await adminConfig();
  const schema = body?.schema as Record<string, unknown> | undefined;
  if (!schema || typeof schema.current !== 'number') return null;
  return {
    current: schema.current,
    oldestSupported: schema.oldest_supported as number,
    declared: typeof schema.declared === 'number' ? schema.declared : null,
    deprecated: Boolean(schema.deprecated),
  };
}
