import type { FileSize } from './file-size';
import type { LastActive } from './when';

type Translate = (key: string, options?: Record<string, unknown>) => string;

/** The words for a size, assembled where there is a translator. */
export function saySize(size: FileSize, t: Translate): string {
  if (size.key === 'when.kilobytes') return t(size.key, { size: size.size });
  if (size.key === 'when.bytes') return t(size.key, { count: size.count });
  return t(size.key);
}

/**
 * The words for when something last happened.
 *
 * The date is formatted in the reader's own locale rather than a
 * fixed one, which is the other half of what this fixes.
 */
export function sayWhen(when: LastActive, t: Translate, locale: string): string {
  switch (when.kind) {
    case 'unknown':
      return '';
    case 'justNow':
      return t('when.justNow');
    case 'ago':
      return t(when.key, { count: when.count });
    default:
      return new Date(when.at).toLocaleDateString(locale, {
        day: 'numeric',
        month: 'long',
      });
  }
}
