import { useTranslation } from 'react-i18next';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, AlertTriangle, CheckCircle } from 'lucide-react';
import { buildAppPath } from '../lib/app-paths';

export function ConsentPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleApprove = async () => {
    setIsSubmitting(true);
    setError(null);

    const maxRetries = 3;
    const baseDelay = 1000;

    for(let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const response = await fetch(buildAppPath('/auth/consent/approve'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({}),
        });

        if (response.ok) {
          const data = await response.json();
          navigate(data.redirectUrl ?? '/', { replace: true });
          return;
        }

        if (attempt < maxRetries) {
          await new Promise(r => setTimeout(r, baseDelay * 2 ** attempt));
          continue;
        }

        throw new Error('Failed to approve consent');
      } catch (err) {
        if (attempt < maxRetries) {
          await new Promise(r => setTimeout(r, baseDelay * 2 ** attempt));
          continue;
        }
        setError(err instanceof Error ? err.message : t('consent.errorOccurred'));
      }
    }

    setIsSubmitting(false);
  };

  return (
    <div className="w-full min-h-screen bg-background flex items-center justify-center p-4">
      <div className="max-w-3xl w-full bg-card rounded-xl shadow-elevated border border-border animate-fadeInUp">
        <div className="p-6 sm:p-8">
          {/* Header */}
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-primary rounded-full flex items-center justify-center mx-auto mb-4">
              <Shield className="w-8 h-8 text-primary-foreground" />
            </div>
            <h1 className="text-2xl font-bold text-foreground mb-2">
              {t('consent.authRequired')}
            </h1>
            <p className="text-muted-foreground">
              {t('consent.needsPermission')}
            </p>
          </div>

          {/* AI Technology Usage Notice */}
          <div className="bg-primary/10 border border-primary/30 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-foreground mb-3">
              {t('consent.aiNotice')}
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {t('consent.aiNoticeBody')}
            </p>
          </div>

          {/* Permissions */}
          <div className="space-y-4 mb-6">
            <div className="bg-secondary rounded-lg p-4 border border-border">
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-green-500 dark:text-green-400 mt-0.5 shrink-0" />
                  {t('consent.ssoTokenUse')}</li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-green-500 dark:text-green-400 mt-0.5 shrink-0" />
                  {t('consent.executeActions')}
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-green-500 dark:text-green-400 mt-0.5 shrink-0" />
                  {t('consent.readAndProcess')}
                </li>
              </ul>
            </div>

            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500 dark:text-amber-400 mt-0.5 shrink-0" />
                <div>
                  <h4 className="font-medium text-foreground mb-1">
                    {t('consent.important')}</h4>
                  <p className="text-sm text-muted-foreground">
                    {t('consent.identityNotice')}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div
              className="bg-destructive/10 border border-destructive/30 rounded-lg p-3 mb-4"
              role="alert"
            >
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleApprove}
              disabled={isSubmitting}
              className="w-full px-4 py-2.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-70 disabled:cursor-not-allowed font-medium text-sm flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary-foreground/30 border-t-primary-foreground" />
                  {t('consent.acknowledging')}</>
              ) : (
                'Acknowledge & Proceed'
              )}
            </button>
          </div>

          {/* Footer */}
          <div className="mt-6 pt-4 border-t border-border">
            <p className="text-xs text-muted-foreground text-center leading-relaxed">
              {t('consent.byAcknowledging')}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
