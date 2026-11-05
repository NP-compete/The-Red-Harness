import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  readPermissions,
  readProfile,
  saveProfile,
  type UserPermissions,
} from '../../services/user-admin-api';

/**
 * Correcting somebody else's profile (E9-T3).
 *
 * **The hiding is not the check.** The agent asks the policy again
 * on the write, so what this screen shows is a courtesy — an
 * operator should not be offered a control that will refuse them —
 * and not a permission boundary. A client that skipped the
 * preflight entirely would gain nothing.
 *
 * **Refused and unavailable are drawn differently.** `allowed`
 * false means the policy said no and the reason is worth reading.
 * `writable_here` false means this deployment has nowhere to put
 * that change: membership and entitlement belong to the identity
 * provider, and no role would make the button work. Showing both
 * as one greyed-out control would send somebody hunting for an
 * administrator who could do it.
 */
export function UserProfileAdmin() {
  const { t } = useTranslation();
  const [userId, setUserId] = useState('');
  const [asked, setAsked] = useState('');
  const [permissions, setPermissions] = useState<UserPermissions | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [writable, setWritable] = useState<string[]>([]);
  const [note, setNote] = useState('');
  const [refused, setRefused] = useState('');

  const look = useCallback(async () => {
    const id = userId.trim();
    if (!id) return;
    setNote('');
    setRefused('');
    const [perms, profile] = await Promise.all([readPermissions(id), readProfile(id)]);
    setPermissions(perms);
    setFields(profile?.fields ?? {});
    setWritable(profile?.writable_fields ?? []);
    setAsked(id);
  }, [userId]);

  useEffect(() => {
    // A new identity in the box invalidates what is on screen. Leaving
    // the previous person's answers visible beside a different name is
    // the kind of thing somebody acts on.
    if (userId.trim() !== asked) {
      setPermissions(null);
      setFields({});
    }
  }, [userId, asked]);

  const profileClass = permissions?.classes.find((c) => c.field_class === 'profile');
  const mayEdit = profileClass?.allowed === true && profileClass.writable_here;

  const onSave = useCallback(async () => {
    setNote('');
    setRefused('');
    const outcome = await saveProfile(asked, fields);
    if (!outcome.ok) {
      setRefused(outcome.detail ?? '');
      return;
    }
    setFields(outcome.fields ?? fields);
    setNote(t('userAdmin.saved'));
  }, [asked, fields, t]);

  return (
    <section className="mb-12">
      <h2 className="mb-2 text-base font-semibold">{t('userAdmin.heading')}</h2>
      <p className="mb-3 text-sm text-muted-foreground">{t('userAdmin.scope')}</p>

      <div className="mb-3 flex items-center gap-2">
        <input
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder={t('userAdmin.whoPlaceholder')}
          aria-label={t('userAdmin.who')}
          className="w-64 rounded border border-border bg-card px-2 py-1 text-sm"
        />
        <button
          type="button"
          onClick={() => void look()}
          className="rounded border border-border px-3 py-1 text-sm"
        >
          {t('userAdmin.look')}
        </button>
      </div>

      {permissions && (
        <>
          <p className="mb-2 text-xs text-muted-foreground">
            {t('userAdmin.roles', {
              actor: permissions.actor_role,
              target: permissions.target_role,
            })}
          </p>

          <ul className="mb-4 space-y-1 text-xs">
            {permissions.classes.map((c) => (
              <li key={c.field_class}>
                <span className="font-mono">{c.field_class}</span>{' '}
                {!c.writable_here ? (
                  <span className="text-muted-foreground">
                    — {t('userAdmin.elsewhere')}
                  </span>
                ) : c.allowed ? (
                  <span>— {t('userAdmin.permitted')}</span>
                ) : (
                  <span className="text-muted-foreground">— {c.reasons[0]}</span>
                )}
              </li>
            ))}
          </ul>

          {mayEdit ? (
            <>
              {writable.map((name) => (
                <label key={name} className="mb-2 block text-sm">
                  <span className="mb-1 block font-mono text-xs">{name}</span>
                  <input
                    value={fields[name] ?? ''}
                    onChange={(e) => setFields({ ...fields, [name]: e.target.value })}
                    className="w-full rounded border border-border bg-card px-2 py-1 text-sm"
                  />
                </label>
              ))}
              <button
                type="button"
                onClick={() => void onSave()}
                className="mt-2 rounded bg-primary px-3 py-1 text-sm text-primary-foreground"
              >
                {t('userAdmin.save')}
              </button>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              {profileClass?.reasons[0] ?? t('userAdmin.noProfileEdit')}
            </p>
          )}

          {note && <p className="mt-2 text-xs text-muted-foreground">{note}</p>}
          {refused && (
            <p className="mt-2 text-xs text-destructive" role="alert">
              {refused}
            </p>
          )}
        </>
      )}
    </section>
  );
}
