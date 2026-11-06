export interface NumericCheckState {
  checked: number;
  unsupported: string[];
}

export interface PresentedNumericCheck {
  warning: string;
  figures: string[];
  detail: string;
  severity: 'medium' | 'high';
}

export function presentNumericCheck(check: NumericCheckState): PresentedNumericCheck | null {
  const count = check.unsupported.length;
  if (count === 0) {
    return null;
  }

  return {
    warning: `${check.unsupported.join(', ')} ${count === 1 ? 'does' : 'do'} not appear in any source`,
    figures: check.unsupported,
    detail: `${count} of ${check.checked} figures could not be traced`,
    // An answer whose every figure is untraceable is not a partial worry.
    severity: count === check.checked ? 'high' : 'medium',
  };
}
