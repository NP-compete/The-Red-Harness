import { describe, expect, it } from 'vitest';

import { presentSetting } from '@/lib/settings-layers-view';

const setting = {
  key: 'model',
  label: 'Model',
  value: 'fastest',
  layer: 'user',
  lockedBy: '',
  shadowed: ['org', 'team'],
  overriddenAttempts: [] as string[],
};

describe('presentSetting', () => {
  it('shows the value in force', () => {
    expect(presentSetting(setting).value).toBe('fastest');
  });

  it('says where the value came from', () => {
    expect(presentSetting(setting).source).toBe('set by you');
  });

  it('names a team setting as the team’s', () => {
    expect(presentSetting({ ...setting, layer: 'team', shadowed: ['org'] }).source).toBe(
      'set by your team',
    );
  });

  it('names an organisation setting as the organisation’s', () => {
    expect(presentSetting({ ...setting, layer: 'org', shadowed: [] }).source).toBe(
      'set by your organisation',
    );
  });

  it('says plainly when a value is just the default', () => {
    expect(presentSetting({ ...setting, layer: 'default', shadowed: [] }).source).toBe(
      'the default',
    );
  });

  it('can be changed when nothing locks it', () => {
    expect(presentSetting(setting).editable).toBe(true);
  });

  it('cannot be changed when a wider layer locked it', () => {
    const locked = { ...setting, layer: 'org', lockedBy: 'org', shadowed: [] };
    expect(presentSetting(locked).editable).toBe(false);
  });

  it('says who locked it', () => {
    const locked = { ...setting, layer: 'org', lockedBy: 'org', shadowed: [] };
    expect(presentSetting(locked).note).toBe('Locked by your organisation');
  });

  it('tells you when your own setting is being ignored', () => {
    const locked = {
      ...setting,
      layer: 'org',
      lockedBy: 'org',
      shadowed: ['user'],
      overriddenAttempts: ['user'],
    };
    expect(presentSetting(locked).note).toBe(
      'Locked by your organisation; your own setting is not being used',
    );
  });

  it('does not claim your setting is ignored when you never set one', () => {
    const locked = { ...setting, layer: 'org', lockedBy: 'org', shadowed: ['team'], overriddenAttempts: ['team'] };
    expect(presentSetting(locked).note).toBe('Locked by your organisation');
  });

  it('says nothing extra for an ordinary setting', () => {
    expect(presentSetting(setting).note).toBe('');
  });

  it('lists what this value is overriding so the layering is visible', () => {
    expect(presentSetting(setting).overriding).toEqual(['org', 'team']);
  });

  it('shows no value as not set', () => {
    const unset = { ...setting, value: null, layer: '', shadowed: [] };
    expect(presentSetting(unset).value).toBe('not set');
  });

  it('lets an unset setting be set', () => {
    const unset = { ...setting, value: null, layer: '', shadowed: [] };
    expect(presentSetting(unset).editable).toBe(true);
  });
});
