import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { buildAppPath } from '../../lib/app-paths';

/**
 * The interface's own configuration (E25).
 *
 * The agent's config surface shows what the *agent* reads. This
 * file is read by this service, from its own working directory,
 * and the agent cannot see it — an edit accepted over there would
 * be stored, echoed back and never applied, which is how it used
 * to behave before `config/ui/settings.yaml` was taken out of the
 * agent's editable set.
 *
 * Read-only, and for a better reason than "not built yet": the
 * file is watched and hot-reloaded, so editing it where it is
 * mounted takes effect without a restart. A write endpoint here
 * would be a second way to change one file.
 */
interface InterfaceConfig {
  path: string;
  hot_reloaded: boolean;
  editable_here: boolean;
  why_readonly: string;
  settings: unknown;
}

export function InterfaceConfigView() {
  const { t } = useTranslation();
  const [cfg, setCfg] = useState<InterfaceConfig | null | undefined>(undefined);

  useEffect(() => {
    let live = true;
    fetch(buildAppPath('/api/config/interface'), { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((body) => live && setCfg(body))
      .catch(() => live && setCfg(null));
    return () => {
      live = false;
    };
  }, []);

  // Still asking, or an older server with no such route. Neither is
  // "this deployment has no interface configuration".
  if (cfg === undefined || cfg === null) return null;

  return (
    <section className="mb-12">
      <h2 className="mb-2 text-base font-semibold">{t('interfaceConfig.heading')}</h2>
      <p className="mb-1 text-sm text-muted-foreground">
        <span className="font-mono text-xs">{cfg.path}</span>
      </p>
      <p className="mb-3 text-sm text-muted-foreground">{cfg.why_readonly}</p>
      <pre className="max-h-96 overflow-auto rounded border border-border bg-card p-2 text-xs">
        {JSON.stringify(cfg.settings, null, 2)}
      </pre>
    </section>
  );
}
