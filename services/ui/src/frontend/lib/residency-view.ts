import i18n from '../i18n';
export interface PlacementState {
  region: string;
  preferredRegion: string;
  degraded: boolean;
  refused: boolean;
  reason: string;
  allowedRegions: string[];
}

export interface PresentedResidency {
  label: string;
  detail: string;
  allowed: string[];
  severity: 'none' | 'low' | 'high';
  action: 'view-policy' | 'none';
}

export function presentResidency(placement: PlacementState): PresentedResidency {
  if (placement.refused) {
    return {
      label: i18n.t('residency.cannotBePlaced'),
      detail: placement.reason,
      allowed: placement.allowedRegions,
      severity: 'high',
      action: 'view-policy',
    };
  }

  return {
    label: placement.degraded
      ? `Running in ${placement.region}, not ${placement.preferredRegion}`
      : `Running in ${placement.region}`,
    detail: placement.degraded ? 'This is still within your allowed regions' : '',
    allowed: placement.allowedRegions,
    severity: placement.degraded ? 'low' : 'none',
    action: 'none',
  };
}
