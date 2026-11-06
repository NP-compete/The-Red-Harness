import { describe, expect, it } from 'vitest';

import { mergeProvenance } from './merge-provenance';

const live = (over: Record<string, unknown> = {}) => ({
  id: 'm1',
  type: 'ai',
  content: 'hi',
  ...over,
});

const stored = (kw: Record<string, unknown>) => ({
  id: 'm1',
  type: 'ai',
  content: 'hi',
  additional_kwargs: kw,
});

describe('mergeProvenance', () => {
  it('brings over what the stream could not carry', () => {
    const [merged] = mergeProvenance([live()], [stored({ pii_scrubbed: 2 })]);
    expect(
      (merged as { additional_kwargs?: Record<string, unknown> }).additional_kwargs,
    ).toMatchObject({ pii_scrubbed: 2 });
  });

  it('leaves the message otherwise untouched', () => {
    const [merged] = mergeProvenance([live()], [stored({ pii_scrubbed: 2 })]);
    expect(merged).toMatchObject({ id: 'm1', content: 'hi' });
  });

  it('matches by id, not by position', () => {
    const merged = mergeProvenance(
      [live({ id: 'a' }), live({ id: 'b' })],
      [{ ...stored({ pii_scrubbed: 9 }), id: 'b' }],
    );
    expect(
      (merged[0] as { additional_kwargs?: unknown }).additional_kwargs,
    ).toBeUndefined();
    expect(
      (merged[1] as { additional_kwargs?: Record<string, unknown> }).additional_kwargs,
    ).toMatchObject({ pii_scrubbed: 9 });
  });

  it('does not overwrite provenance the stream already delivered', () => {
    const withModel = live({ additional_kwargs: { model: 'live-model' } });
    const [merged] = mergeProvenance(
      [withModel],
      [stored({ model: 'stored', pii_scrubbed: 1 })],
    );
    const kw = (merged as { additional_kwargs: Record<string, unknown> })
      .additional_kwargs;
    expect(kw.model).toBe('live-model');
    expect(kw.pii_scrubbed).toBe(1);
  });

  it('returns the same list when there is nothing to add', () => {
    const messages = [live()];
    expect(
      mergeProvenance(messages, [{ id: 'm1', type: 'ai', content: 'hi' }]),
    ).toEqual(messages);
  });

  it('ignores saved messages the view does not have', () => {
    const merged = mergeProvenance(
      [live()],
      [{ ...stored({ pii_scrubbed: 3 }), id: 'other' }],
    );
    expect(
      (merged[0] as { additional_kwargs?: unknown }).additional_kwargs,
    ).toBeUndefined();
  });

  it('copes with a message that has no id', () => {
    const merged = mergeProvenance(
      [{ type: 'ai', content: 'x' }],
      [stored({ pii_scrubbed: 1 })],
    );
    expect(merged).toHaveLength(1);
  });

  it('hands back the very same list when nothing changed', () => {
    // The caller redraws the conversation on a new list, so a merge
    // that found nothing must not look like a change.
    const messages = [live()];
    expect(mergeProvenance(messages, [stored({})])).toBe(messages);
  });

  it('copes with nothing saved at all', () => {
    const messages = [live()];
    expect(mergeProvenance(messages, [])).toEqual(messages);
  });
});
