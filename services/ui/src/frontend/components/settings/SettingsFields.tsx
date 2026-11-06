import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { readSettingsView, type SettingsView } from '../../services/config-editing-api';

/**
 * The configuration that is not in a file.
 *
 * The editor above lists the seven paths this deployment will let
 * somebody change, and the drift view says which of them were. Both
 * answer "what has been edited". Neither answers "how is this
 * deployment wired", because most of that comes from the process
 * environment — 243 fields, none of them previously on any screen.
 * Somebody reading the editable paths reasonably concluded they had
 * seen the configuration.
 *
 * Read-only, and it says so in the agent's own words rather than by
 * omitting a button — the same rule the editor follows for a
 * read-only deployment.
 *
 * Secrets are masked by the agent, never here. A client that
 * receives the value and declines to draw it has already put it in
 * the browser and in anything watching the network. The masked count
 * is shown so the screen cannot hide more than it admits to.
 */
export function SettingsFields() {
  const { t } = useTranslation();
  const [view, setView] = useState<SettingsView | null | undefined>(undefined);
  const [filter, setFilter] = useState('');
  const [onlySet, setOnlySet] = useState(false);

  useEffect(() => {
    let live = true;
    void readSettingsView().then((v) => live && setView(v));
    return () => {
      live = false;
    };
  }, []);

  const rows = useMemo(() => {
    if (!view) return [];
    const needle = filter.trim().toLowerCase();
    return view.fields.filter(
      (f) => (!onlySet || f.from_env) && (!needle || f.name.toLowerCase().includes(needle)),
    );
  }, [view, filter, onlySet]);

  // Still asking, or an agent without the route. Neither is "this
  // deployment has no settings", and drawing an empty table would
  // say exactly that.
  if (view === undefined || view === null) return null;

  return (
    <section className="mb-12">
      <h2 className="mb-2 text-base font-semibold">{t('settingsFields.heading')}</h2>
      <p className="mb-1 text-sm text-muted-foreground">
        {t('settingsFields.summary', {
          total: view.total,
          fromEnv: view.from_env,
          overridden: view.overridden,
          masked: view.masked,
        })}
      </p>
      {/* Which overrides raised a limit, above the list rather than
          inside it: "twelve differ from their defaults" is a number
          to scroll past, and "these two raised a limit" is the one
          an operator came to find. */}
      {view.loosened.length > 0 && (
        <p className="mb-2 rounded border border-amber-500/60 p-2 text-sm">
          {t('settingsFields.loosened', { count: view.loosened.length })}
          <span className="mt-1 block break-all font-mono text-xs">
            {view.loosened.join(', ')}
          </span>
        </p>
      )}
      <p className="mb-3 text-sm text-muted-foreground">{view.why_readonly}</p>

      <div className="mb-2 flex items-center gap-3">
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder={t('settingsFields.filter')}
          aria-label={t('settingsFields.filter')}
          className="w-64 rounded border border-border px-2 py-1 text-sm"
        />
        <label className="flex items-center gap-1 text-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={onlySet}
            onChange={(e) => setOnlySet(e.target.checked)}
          />
          {t('settingsFields.onlySet')}
        </label>
      </div>

      <div className="max-h-96 overflow-auto rounded border border-border">
        <table className="w-full text-xs">
          <tbody>
            {rows.map((f) => (
              <tr key={f.name} className="border-b border-border/50 align-top">
                <td className="py-1 pl-2 pr-3 font-mono">{f.name}</td>
                <td className="py-1 pr-3 break-all font-mono">{String(f.value ?? '')}</td>
                <td className="py-1 pr-2 whitespace-nowrap text-muted-foreground">
                  {f.from_env
                    ? t('settingsFields.fromEnv')
                    : t('settingsFields.fromDefault')}
                  {f.overridden ? ` · ${t('settingsFields.overridden')}` : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && (
          <p className="p-2 text-sm text-muted-foreground">
            {t('settingsFields.noMatches')}
          </p>
        )}
      </div>
    </section>
  );
}
