/**
 * Whether a server's own credential is there.
 *
 * A server set to use an API key whose key is absent looks
 * exactly like one that works — the dot is green because the
 * server is enabled, and nothing says the call will fail
 * until somebody makes one.
 *
 * Only worth saying when it is wrong. A deployment with
 * thirteen servers configured correctly does not need
 * thirteen rows each confirming it; a line that appears on
 * every row is one nobody reads on the row that mattered.
 */

import { describe, expect, it } from 'vitest';

import { credentialWarning } from './credential-state';

describe('when something is wrong', () => {
  it('says so when the credential is missing', () => {
    expect(credentialWarning({ enabled: true, credential: 'missing' })).not.toBeNull();
  });

  it('names what to do about it', () => {
    // "Credential missing" is a fact. What makes it
    // actionable is that it is the deployment's own key,
    // set outside this interface.
    const said = credentialWarning({ enabled: true, credential: 'missing' });
    expect(said?.toLowerCase()).toMatch(/key|credential|secret/);
  });
});

describe('when nothing is', () => {
  it('says nothing when the credential is there', () => {
    expect(credentialWarning({ enabled: true, credential: 'set' })).toBeNull();
  });

  it('says nothing for a server that borrows your identity', () => {
    // Nothing could be absent, so a warning would send
    // somebody looking for a variable that should not exist.
    expect(credentialWarning({ enabled: true, credential: 'not needed' })).toBeNull();
  });

  it('says nothing for a disabled server', () => {
    // It reaches nothing, so its credential cannot matter.
    // Warning anyway is noise on every deliberately-off row.
    expect(credentialWarning({ enabled: false, credential: 'missing' })).toBeNull();
  });

  it('says nothing when the agent did not report one', () => {
    // An older agent that has never been asked is not a
    // server with a missing key.
    expect(credentialWarning({ enabled: true })).toBeNull();
  });

  it('says nothing for a value it does not recognise', () => {
    expect(
      credentialWarning({ enabled: true, credential: 'something-else' as never }),
    ).toBeNull();
  });
});
