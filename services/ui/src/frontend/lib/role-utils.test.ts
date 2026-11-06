import { afterEach, describe, expect, it } from 'vitest';

import {
  isPrivilegedUser,
  privilegeKnown,
  rememberAgentRole,
  rememberAuthEnabled,
} from './role-utils';

function appData(data: Record<string, unknown> | undefined) {
  (window as unknown as { APP_DATA?: unknown }).APP_DATA = data;
}

afterEach(() => {
  appData(undefined);
  rememberAuthEnabled(undefined);
  rememberAgentRole(undefined);
});

describe('isPrivilegedUser', () => {
  it('lets an owner through', () => {
    appData({ userRole: 'owners' });
    expect(isPrivilegedUser()).toBe(true);
  });

  it('lets a builder through', () => {
    appData({ userRole: 'builders' });
    expect(isPrivilegedUser()).toBe(true);
  });

  it('keeps an ordinary user out', () => {
    appData({ userRole: 'users' });
    expect(isPrivilegedUser()).toBe(false);
  });

  it('keeps an ordinary user out even with sign-in switched off', () => {
    // A declared role is an answer, and it outranks the guess below.
    appData({ userRole: 'users', features: { auth_enabled: false } });
    expect(isPrivilegedUser()).toBe(false);
  });

  it('treats a nameless user as privileged when nobody is signing in', () => {
    // With sign-in off there is no role to read and nobody to tell
    // apart, so hiding operator surfaces hides them from everyone.
    appData({ features: { auth_enabled: false } });
    expect(isPrivilegedUser()).toBe(true);
  });

  it('keeps a nameless user out while sign-in is on', () => {
    appData({ features: { auth_enabled: true } });
    expect(isPrivilegedUser()).toBe(false);
  });

  it('keeps a nameless user out when nothing says either way', () => {
    appData({});
    expect(isPrivilegedUser()).toBe(false);
  });

  it('survives there being no app data at all', () => {
    appData(undefined);
    expect(isPrivilegedUser()).toBe(false);
  });

  it('takes the answer from the loaded settings when the page did not carry one', () => {
    // The flag arrives with the rest of the configuration, after the
    // page was served, so it is not in the data embedded in the HTML.
    appData({});
    rememberAuthEnabled(false);
    expect(isPrivilegedUser()).toBe(true);
  });

  it('keeps a nameless user out when the loaded settings require sign-in', () => {
    appData({});
    rememberAuthEnabled(true);
    expect(isPrivilegedUser()).toBe(false);
  });

  it('still lets a declared role decide', () => {
    appData({ userRole: 'users' });
    rememberAuthEnabled(false);
    expect(isPrivilegedUser()).toBe(false);
  });
});

describe('privilegeKnown', () => {
  it('knows the answer when a role was declared', () => {
    appData({ userRole: 'users' });
    expect(privilegeKnown()).toBe(true);
  });

  it('knows the answer once the settings have loaded', () => {
    appData({});
    rememberAuthEnabled(false);
    expect(privilegeKnown()).toBe(true);
  });

  it('knows the answer when the page carried the flag itself', () => {
    appData({ features: { auth_enabled: true } });
    expect(privilegeKnown()).toBe(true);
  });

  it('does not yet know before anything has said either way', () => {
    // Deciding here sends an allowed reader away from a page they can
    // open, a moment before the answer arrives.
    appData({});
    expect(privilegeKnown()).toBe(false);
  });
});

describe('the role the agent itself reports', () => {
  it('lets an owner through on the agent’s word alone', () => {
    appData({});
    rememberAgentRole('owners');
    expect(isPrivilegedUser()).toBe(true);
  });

  it('keeps an ordinary user out on the same word', () => {
    appData({});
    rememberAgentRole('users');
    expect(isPrivilegedUser()).toBe(false);
  });

  it('outranks the guess made from sign-in being off', () => {
    appData({});
    rememberAuthEnabled(false);
    rememberAgentRole('users');
    expect(isPrivilegedUser()).toBe(false);
  });

  it('yields to a role the page declared', () => {
    appData({ userRole: 'users' });
    rememberAgentRole('owners');
    expect(isPrivilegedUser()).toBe(false);
  });

  it('settles the question on its own', () => {
    appData({});
    rememberAgentRole('users');
    expect(privilegeKnown()).toBe(true);
  });
});
