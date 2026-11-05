import { describe, expect, it } from 'vitest';

import { fileSize } from './file-size';

import en from '../i18n/locales/en.json';

/**
 * These describe rather than word: the translator lives in a
 * component. Resolving through English keeps each assertion about
 * the sentence a person reads, and proves the key exists.
 */
function said(shape: { key: string; count?: number; size?: string } | null): string {
  if (!shape) return '';
  const [section, name] = shape.key.split('.');
  const table = (en as Record<string, Record<string, string>>)[section] ?? {};
  const form =
    shape.count === undefined
      ? table[name]
      : table[`${name}_${shape.count === 1 ? 'one' : 'other'}`] ?? table[name];
  if (form === undefined) throw new Error(`no English string for '${shape.key}'`);
  return form
    .replace('{{count}}', String(shape.count ?? ''))
    .replace('{{size}}', String(shape.size ?? ''));
}


describe('fileSize', () => {
  it('counts a small file in bytes', () => {
    expect(said(fileSize(21))).toBe('21 bytes');
  });

  it('counts a larger one in kilobytes', () => {
    expect(said(fileSize(1200))).toBe('1.2 kB');
  });

  it('switches over at a thousand', () => {
    expect(said(fileSize(999))).toBe('999 bytes');
    expect(said(fileSize(1000))).toBe('1.0 kB');
  });

  it('says one byte in the singular', () => {
    expect(said(fileSize(1))).toBe('1 byte');
  });

  it('calls an empty file empty rather than zero bytes', () => {
    expect(said(fileSize(0))).toBe('empty');
  });

  it('does not report a negative size', () => {
    expect(said(fileSize(-5))).toBe('empty');
  });
});
