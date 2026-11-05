import { buildAppPath } from '../lib/app-paths';

/**
 * Administrator reads and writes against a person's profile (E9).
 *
 * The permissions call exists so a screen can hide what the policy
 * would refuse. It is not the check — the agent asks the policy
 * again on the write, so a stale preflight authorises nothing and
 * a client that skipped this call gains no access by doing so.
 */

const BASE = '/api/proxy/agent/admin/users';

export interface ClassPermission {
  field_class: string;
  allowed: boolean;
  reasons: string[];
  /** The policy may permit a class this deployment cannot write.
      Separate from `allowed` so a screen does not offer a control
      that answers 400. */
  writable_here: boolean;
}

export interface UserPermissions {
  user_id: string;
  actor_role: string;
  target_role: string;
  classes: ClassPermission[];
}

export interface UserProfile {
  user_id: string;
  fields: Record<string, string>;
  writable_fields: string[];
}

export interface SaveOutcome {
  ok: boolean;
  detail?: string;
  fields?: Record<string, string>;
}

export async function readPermissions(userId: string): Promise<UserPermissions | null> {
  try {
    const response = await fetch(buildAppPath(`${BASE}/${encodeURIComponent(userId)}/permissions`), {
      credentials: 'include',
    });
    if (!response.ok) return null;
    return (await response.json()) as UserPermissions;
  } catch {
    return null;
  }
}

export async function readProfile(userId: string): Promise<UserProfile | null> {
  try {
    const response = await fetch(buildAppPath(`${BASE}/${encodeURIComponent(userId)}/profile`), {
      credentials: 'include',
    });
    if (!response.ok) return null;
    return (await response.json()) as UserProfile;
  } catch {
    return null;
  }
}

export async function saveProfile(
  userId: string,
  fields: Record<string, string>,
): Promise<SaveOutcome> {
  try {
    const response = await fetch(buildAppPath(`${BASE}/${encodeURIComponent(userId)}/profile`), {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fields }),
    });
    const body = (await response.json().catch(() => ({}))) as {
      message?: string;
      fields?: Record<string, string>;
    };
    if (response.ok) return { ok: true, fields: body.fields };
    // The agent's own sentence. It knows whether this was a role
    // the policy refused or a field that belongs to the identity
    // provider, and those have different answers for the reader.
    return { ok: false, detail: body.message ?? 'That change was not saved.' };
  } catch {
    return { ok: false, detail: 'Could not reach the agent.' };
  }
}
