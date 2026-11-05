/**
 * Which configuration layout a pod reads, and which one it was given.
 *
 * Both, because either alone is unreadable. A tree declaring version
 * 2 is fine on one image and refused on the next, and the only way
 * to know which is to see the window beside it.
 */

export interface SchemaWindow {
  current: number;
  oldestSupported: number;
  /** `null` when the tree carries no version field at all. */
  declared: number | null;
  deprecated: boolean;
}

export interface SchemaDescription {
  /** `null` when the tree declares nothing — not the version it is read as. */
  declared: string | null;
  accepts: string;
  ageing: boolean;
}

export function describeSchema(
  found: SchemaWindow | null,
): SchemaDescription | null {
  // An older build that has never heard of the question is not a
  // deployment running version 0.
  if (
    !found ||
    typeof found.current !== 'number' ||
    typeof found.oldestSupported !== 'number'
  ) {
    return null;
  }

  const { current, oldestSupported } = found;
  return {
    declared: typeof found.declared === 'number' ? String(found.declared) : null,
    accepts:
      oldestSupported === current
        ? String(current)
        : `${oldestSupported}–${current}`,
    ageing: Boolean(found.deprecated),
  };
}
