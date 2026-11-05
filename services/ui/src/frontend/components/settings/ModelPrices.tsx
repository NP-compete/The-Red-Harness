import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { getModelPrices, type ModelPrices as Prices } from '../../services/rates-api';

/**
 * What model calls are priced at here.
 *
 * A conversation can show what it cost, but a figure in money is only
 * as good as the price behind it — and a deployment that has set no
 * prices must say so rather than let every run look free.
 */
export function ModelPrices() {
  const { t } = useTranslation();
  const [prices, setPrices] = useState<Prices | null>(null);

  useEffect(() => {
    let alive = true;
    void getModelPrices().then((found) => {
      if (alive) setPrices(found);
    });
    return () => {
      alive = false;
    };
  }, []);

  if (!prices) {
    return null;
  }

  // The ceiling belongs beside the prices: it is quoted in the same
  // currency and means nothing without them.
  const ceiling = prices.runLimit ? (
    <p className="text-xs text-muted-foreground">
      {t('prices.stopAt', { limit: prices.runLimit, currency: prices.currency })}
      {prices.runWarnAt ? t('prices.warnAt', { amount: prices.runWarnAt }) : ''}.
      {prices.rates.length === 0 && t('prices.unreachable')}
    </p>
  ) : null;

  if (prices.rates.length === 0) {
    return (
      <div className="space-y-1 text-sm text-muted-foreground">
        <p>
          {t('prices.none')}
        </p>
        {prices.problem ? (
          <p className="text-destructive">{prices.problem}</p>
        ) : (
          <p>
            {t('prices.readFrom')} <code className="text-xs">{prices.source}</code>.
          </p>
        )}
        {ceiling}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {t('prices.list', { version: prices.version, currency: prices.currency })}
      </p>
      {ceiling}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-muted-foreground">
            <th scope="col" className="pb-1 font-normal">
              {t('prices.model')}
            </th>
            <th scope="col" className="pb-1 font-normal">
              {t('prices.sent')}
            </th>
            <th scope="col" className="pb-1 font-normal">
              {t('prices.received')}
            </th>
          </tr>
        </thead>
        <tbody>
          {prices.rates.map((rate) => (
            <tr key={rate.model} className="border-t border-border">
              <td className="py-1.5">
                <code className="text-xs text-foreground">{rate.model}</code>
              </td>
              <td className="py-1.5 tabular-nums text-muted-foreground">
                {rate.inputPer1k}
              </td>
              <td className="py-1.5 tabular-nums text-muted-foreground">
                {rate.outputPer1k}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
