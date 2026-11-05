import { buildAppPath } from '../lib/app-paths';
import type { ConfigFile } from '../lib/config-drift';

/**
 * Talking to the agent about its own configuration.
 *
 * One rule shapes all of it: a deployment that has not been
 * opened for editing has no write routes at all, so the answer
 * is 404 rather than a refusal. That is the ordinary state and
 * not a fault — reporting it as a failure would tell somebody
 * something is broken when the deployment is behaving exactly
 * as it was configured to.
 */

const BASE = '/api/proxy/agent/config';

// Agent-owned shapes come from the generated contract rather than
// being described twice (E10-T14).
export type { EditingState, ConfigTree, ConfigTreeFile, ConfigFileText, SettingsView, SettingsField } from '../types/contract';
import type {
  ConfigTree as ConfigTreeType,
  ConfigFileText as ConfigFileTextType,
  EditingState as EditingStateType,
  SettingsView as SettingsViewType,
} from '../types/contract';

export interface Outcome {
  ok: boolean;
  detail?: string;
  /**
   * Whether the change outlives a restart.
   *
   * Reported on every success rather than assumed, because the
   * only store built so far keeps edits in the process and
   * somebody who is not told will find their change gone a day
   * later with nothing connecting the two.
   */
  durable?: boolean;
  /** The version the caller now holds, so a second save from the
      same editor is not a conflict with its own first one. */
  version?: number;
}

/** One file as the agent reads it now, edits included. */
export async function readConfigFile(
  path: string,
): Promise<ConfigFileTextType | null> {
  try {
    const response = await fetch(
      buildAppPath(`${BASE}/file?path=${encodeURIComponent(path)}`),
      { credentials: 'include' },
    );
    if (!response.ok) return null;
    const body = (await response.json()) as Partial<ConfigFileTextType>;
    if (typeof body.content !== 'string') return null;
    return {
      path,
      content: body.content,
      exists: body.exists === true,
      version: typeof body.version === 'number' ? body.version : 0,
      /* Sections this file contains and does not decide. Passed
         through rather than dropped: the agent works it out and
         the person about to edit one is the one who needs it. */
      inert: Array.isArray(body.inert) ? body.inert : [],
    };
  } catch {
    return null;
  }
}

export async function saveConfigFile(
  path: string,
  content: string,
  /**
   * The version loaded with the text. The agent refuses a save
   * against a version that has moved, which is what stops the
   * second person with this file open erasing the first one's
   * edit (MU-5).
   */
  baseVersion?: number,
): Promise<Outcome> {
  try {
    const response = await fetch(buildAppPath(`${BASE}/edit`), {
      method: 'PUT',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, content, base_version: baseVersion }),
    });
    if (response.ok) {
      const body = (await response.json().catch(() => ({}))) as {
        durable?: boolean;
        version?: number;
      };
      return { ok: true, durable: body.durable !== false, version: body.version };
    }
    if (response.status === 404) {
      return {
        ok: false,
        detail:
          'This deployment is read-only, so its configuration cannot be ' +
          'changed from here.',
      };
    }
    // The agent names the file and the field it objected to.
    // Replacing that with a generic failure sends somebody
    // reading their own diff for a problem already located.
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    return { ok: false, detail: body.detail ?? 'That change was not saved.' };
  } catch {
    return { ok: false, detail: 'Could not reach the agent.' };
  }
}

/** `null` when the agent could not be asked — never a guess. */
export async function readEditingState(): Promise<EditingStateType | null> {
  try {
    const response = await fetch(buildAppPath(`${BASE}/editing`), {
      credentials: 'include',
    });
    if (!response.ok) return null;
    const body = (await response.json()) as Partial<EditingStateType>;
    if (typeof body.mode !== 'string') return null;
    return {
      mode: body.mode,
      editable: body.editable === true,
      paths: body.paths ?? [],
      // An agent that predates these fields reports no store and
      // claims no durability — the cautious reading, and the one
      // that shows the warning rather than hiding it.
      store: body.store ?? '',
      durable: body.durable === true,
    };
  } catch {
    return null;
  }
}

/**
 * The paths this deployment has overridden.
 *
 * An empty list and `null` mean different things and are kept
 * apart: nothing has drifted, against could not ask. They read
 * very differently on screen.
 */
export async function readConfigDrift(): Promise<ConfigFile[] | null> {
  try {
    const response = await fetch(buildAppPath(`${BASE}/drift`), {
      credentials: 'include',
    });
    if (!response.ok) return null;
    const body = (await response.json()) as { paths?: ConfigFile[] };
    return Array.isArray(body.paths) ? body.paths : null;
  } catch {
    return null;
  }
}

export interface StoredVersion {
  version: number;
  author: string;
  at: string;
  /** `null` for an adopted baseline: no content, not empty content. */
  content: string | null;
}

/** Every version of one path, oldest first. `null` if it could not be asked. */
export async function readConfigHistory(
  path: string,
): Promise<StoredVersion[] | null> {
  try {
    const response = await fetch(
      buildAppPath(`${BASE}/history?path=${encodeURIComponent(path)}`),
      { credentials: 'include' },
    );
    if (!response.ok) return null;
    const body = (await response.json()) as { versions?: StoredVersion[] };
    return Array.isArray(body.versions) ? body.versions : null;
  } catch {
    return null;
  }
}

export async function revertConfig(
  path: string,
  version: number,
): Promise<Outcome> {
  try {
    const response = await fetch(buildAppPath(`${BASE}/revert`), {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, version }),
    });
    if (response.ok) return { ok: true };
    if (response.status === 404) {
      // Either the deployment is read-only or that version is
      // not there. The agent says which; only the bare 404 of
      // an absent route has no body to say it with.
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      return {
        ok: false,
        detail:
          body.detail ??
          'This deployment is read-only, so its configuration cannot be ' +
            'changed from here.',
      };
    }
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    return { ok: false, detail: body.detail ?? 'That change was not made.' };
  } catch {
    return { ok: false, detail: 'Could not reach the agent.' };
  }
}

export async function adoptBaseline(path: string): Promise<Outcome> {
  try {
    const response = await fetch(buildAppPath(`${BASE}/adopt-baseline`), {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
    if (response.ok) return { ok: true };
    if (response.status === 404) {
      return {
        ok: false,
        detail:
          'This deployment is read-only, so its configuration cannot be ' +
          'changed from here.',
      };
    }
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    return { ok: false, detail: body.detail ?? 'That change was not made.' };
  } catch {
    return { ok: false, detail: 'Could not reach the agent.' };
  }
}

/**
 * Every file in the config root, editable or not.
 *
 * Null when the agent has no such route — an older agent, which is
 * an ordinary state and not a fault. Callers fall back to the
 * editable paths from `/config/editing`, which is what they used
 * before this existed.
 */
export async function readConfigTree(): Promise<ConfigTreeType | null> {
  try {
    const response = await fetch(buildAppPath(`${BASE}/tree`), {
      credentials: 'include',
    });
    if (!response.ok) return null;
    const body = (await response.json()) as ConfigTreeType;
    return Array.isArray(body.files) ? body : null;
  } catch {
    return null;
  }
}

/**
 * The configuration that is not in a file.
 *
 * Null rather than an error on failure, the same as
 * `readConfigDrift`: an older agent has no such route, and that is
 * the ordinary state of a deployment that has not been updated, not
 * a fault worth reporting as one.
 */
export async function readSettingsView(): Promise<SettingsViewType | null> {
  try {
    const response = await fetch(buildAppPath(`${BASE}/settings`), {
      credentials: 'include',
    });
    if (!response.ok) return null;
    const body = (await response.json()) as SettingsViewType;
    return Array.isArray(body.fields) ? body : null;
  } catch {
    return null;
  }
}

/** Where the effective tree is downloaded from. */
export function exportPath(): string {
  return buildAppPath(`${BASE}/export`);
}

export interface GraphNode {
  id: string;
  kind: string;
  label: string;
  path: string | null;
  /** True for a name something references and nothing declares. */
  missing?: boolean;
  tier?: string | null;
  error?: string | null;
  /** On a subagent: the model its front matter names, if any. */
  model?: string | null;
}

export interface GraphEdge {
  from: string;
  to: string;
  kind: string;
  /** Why this reference does not resolve, in words, or null. */
  broken: string | null;
}

export interface ConfigGraph {
  root: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  problems: { where: string; what: string }[];
  element_types: string[];
  counts: Record<string, number>;
}

/**
 * The configuration as a diagram (E34).
 *
 * Null on anything other than a clean answer, like the rest of this
 * file: an agent with no such route is a deployment that has not been
 * updated, not a configuration with no shape.
 */
export async function readConfigGraph(): Promise<ConfigGraph | null> {
  try {
    const response = await fetch(buildAppPath(`${BASE}/graph`), {
      credentials: 'include',
    });
    if (!response.ok) return null;
    const body = (await response.json()) as ConfigGraph;
    return Array.isArray(body.nodes) ? body : null;
  } catch {
    return null;
  }
}

export interface GraphEditResult extends Outcome {
  /** The file the change lands in. */
  path?: string;
  /** What the file would say. Present on a preview, absent on a write. */
  content?: string;
  written?: boolean;
}

/**
 * Change one field on one box in the diagram (E34-T3).
 *
 * `preview` asks what the file *would* say without writing it, which
 * is what makes the change reviewable: a diagram that writes on a
 * click is a diagram nobody dares use. The write itself goes through
 * the same validation, allowlist, version check and history as a
 * typed edit, because on the agent side it is the same function.
 */
export async function editFromGraph(
  nodeId: string,
  field: string,
  value: unknown,
  options: { preview?: boolean; baseVersion?: number } = {},
): Promise<GraphEditResult> {
  try {
    const response = await fetch(buildAppPath(`${BASE}/graph/edit`), {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        node_id: nodeId,
        field,
        value,
        preview: options.preview ?? false,
        base_version: options.baseVersion ?? null,
      }),
    });
    const body = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    if (!response.ok) {
      return {
        ok: false,
        // The agent's own sentence. These refusals name the thing
        // that is wrong — a list that would lose its comments, a
        // version that moved — and a generic message would throw
        // away the only useful part.
        detail:
          (body.message as string) ??
          (body.detail as string) ??
          `The agent refused the change (${response.status}).`,
      };
    }
    return {
      ok: true,
      path: body.path as string,
      content: body.content as string | undefined,
      written: body.written === true,
      version: typeof body.version === 'number' ? body.version : undefined,
      durable: typeof body.durable === 'boolean' ? body.durable : undefined,
    };
  } catch {
    return { ok: false, detail: 'The agent could not be reached.' };
  }
}
