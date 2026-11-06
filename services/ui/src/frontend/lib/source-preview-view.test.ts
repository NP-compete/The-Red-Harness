import { describe, expect, it } from 'vitest';

import { presentSourcePreview } from '@/lib/source-preview-view';

const preview = {
  document: 'handbook',
  chunks: [
    { index: 1, text: 'four five six' },
    { index: 2, text: 'seven eight nine' },
    { index: 3, text: 'ten eleven twelve' },
  ],
  matchedIndex: 2,
  trimmed: false,
  words: 9,
  updatedAt: '2026-10-01T09:00:00Z',
};

const now = new Date('2026-10-27T09:00:00Z');

describe('presentSourcePreview', () => {
  it('names the document', () => {
    expect(presentSourcePreview(preview, now).title).toBe('handbook');
  });

  it('marks the part that matched', () => {
    const parts = presentSourcePreview(preview, now).parts;
    expect(parts.map((part) => part.matched)).toEqual([false, true, false]);
  });

  it('keeps the surrounding text in order', () => {
    const parts = presentSourcePreview(preview, now).parts;
    expect(parts.map((part) => part.text)).toEqual([
      'four five six',
      'seven eight nine',
      'ten eleven twelve',
    ]);
  });

  it('says when surrounding text was left out', () => {
    const tight = { ...preview, chunks: [preview.chunks[1]], trimmed: true };
    expect(presentSourcePreview(tight, now).note).toBe('Surrounding text was left out for space');
  });

  it('adds no note when nothing was left out', () => {
    expect(presentSourcePreview(preview, now).note).toBe('');
  });

  it('says when the document was last updated', () => {
    expect(presentSourcePreview(preview, now).updated).toBe('updated 26 days ago');
  });

  it('says plainly when the update date is unknown', () => {
    const undated = { ...preview, updatedAt: null };
    expect(presentSourcePreview(undated, now).updated).toBe('update date unknown');
  });

  it('offers to open the whole document', () => {
    expect(presentSourcePreview(preview, now).action).toBe('open-document');
  });

  it('says how much was shown', () => {
    expect(presentSourcePreview(preview, now).extent).toBe('9 words from 3 passages');
  });

  it('uses the singular for a lone passage', () => {
    const lone = { ...preview, chunks: [preview.chunks[1]], words: 3, trimmed: true };
    expect(presentSourcePreview(lone, now).extent).toBe('3 words from 1 passage');
  });

  it('refuses to render a preview with nothing in it', () => {
    const empty = { ...preview, chunks: [], words: 0 };
    expect(presentSourcePreview(empty, now).parts).toEqual([]);
  });

  it('says plainly when there is nothing to show', () => {
    const empty = { ...preview, chunks: [], words: 0 };
    expect(presentSourcePreview(empty, now).extent).toBe('nothing to show');
  });
});
