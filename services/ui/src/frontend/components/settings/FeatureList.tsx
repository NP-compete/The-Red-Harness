import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Switch } from '@patternfly/react-core';
import { AlertTriangle, Lock } from 'lucide-react';

import { presentFeature, type FeatureFact } from '../../lib/feature-view';
import { readFeatures, writeFeature } from '../../services/features-api';

/**
 * The optional capabilities, and why each is where it is.
 *
 * Every one ships off. A switch appears only where throwing it
 * would actually do something — the deployment's own flags, with
 * their preconditions met. Everything else is shown with the reason
 * it cannot be changed here, because a switch that posts and is
 * refused is worse than no switch at all.
 *
 * The rules are the agent's and are enforced there. This asks, and
 * repeats what it is told.
 */
export function FeatureList() {
  const { t } = useTranslation();
  const [facts, setFacts] = useState<FeatureFact[] | null>(null);
  const [unreadable, setUnreadable] = useState(false);
  // What the agent said when it would not make a change. Shown
  // against the capability it refused, because a switch that snaps
  // back with no sentence beside it reads as a bug.
  const [refused, setRefused] = useState<Record<string, string>>({});

  const change = async (key: string, next: boolean) => {
    setRefused((had) => {
      const left = { ...had };
      delete left[key];
      return left;
    });
    const result = await writeFeature(key, next);
    if (!result.ok) {
      setRefused((had) => ({ ...had, [key]: result.reason ?? t('features.refused') }));
      return;
    }
    // Re-read rather than assume. The change may have moved
    // something else: a precondition coming on makes whatever
    // needed it settable too.
    const report = await readFeatures();
    setFacts(report.features);
    setUnreadable(report.unreadable);
  };

  useEffect(() => {
    let live = true;
    void readFeatures().then((report) => {
      if (!live) return;
      setFacts(report.features);
      setUnreadable(report.unreadable);
    });
    return () => {
      live = false;
    };
  }, []);

  // Nothing is claimed while the answer is still outstanding: an
  // empty list shown early reads as "there are none".
  if (facts === null) {
    return null;
  }

  if (unreadable) {
    return (
      <div role="alert" className="flex items-start gap-2 text-sm text-amber-500">
        <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" aria-hidden="true" />
        <span>{t('features.unreadable')}</span>
      </div>
    );
  }

  if (facts.length === 0) {
    return <p className="text-sm text-muted-foreground">{t('features.none')}</p>;
  }

  return (
    <ul className="list-none space-y-3">
      {facts.map((fact) => {
        const shown = presentFeature(fact);
        return (
          <li key={shown.key} className="rounded-lg border border-border p-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-foreground">{shown.key}</span>
              <span className="rounded bg-secondary px-1.5 py-0.5 text-[11px] text-muted-foreground">
                {t(`features.scope.${fact.scope}`)}
              </span>
              <span className="ml-auto text-xs text-muted-foreground">
                {t(`features.state.${shown.state}`)}
              </span>
              {/* A switch only where throwing it would do something.
                  One that posts and is refused is worse than none. */}
              {shown.changeable && fact.scope === 'deployment' ? (
                <Switch
                  id={`feature-${shown.key}`}
                  aria-label={shown.key}
                  isChecked={fact.enabled}
                  onChange={(_e, next) => void change(shown.key, next)}
                />
              ) : (
                <Lock className="h-3 w-3 text-muted-foreground" aria-hidden="true" />
              )}
            </div>
            {shown.cost && (
              <p className="mt-1 text-xs text-muted-foreground">{shown.cost}</p>
            )}
            {/* The reason a switch will not move, said before anyone
                reaches for it rather than after. */}
            {shown.needs.length > 0 && (
              <p className="mt-1 text-xs text-amber-500/90">
                {t('features.needs', { names: shown.needs.join(', ') })}
              </p>
            )}
            {shown.blockedBy && (
              <p className="mt-1 text-xs text-amber-500/90">
                {t('features.blockedBy', { level: t(`features.scope.${shown.blockedBy}`) })}
              </p>
            )}
            {refused[shown.key] && (
              <p role="alert" className="mt-1 text-xs text-destructive">
                {refused[shown.key]}
              </p>
            )}
            {shown.needs.length === 0 && !shown.blockedBy && (
              <p className="mt-1 text-[11px] text-muted-foreground">
                {t('features.decidedBy', { level: shown.decidedBy })}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
