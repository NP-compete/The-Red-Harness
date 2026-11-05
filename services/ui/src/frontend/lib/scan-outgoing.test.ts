import { describe, expect, it } from 'vitest';

import { scanOutgoing } from './scan-outgoing';

describe('scanOutgoing', () => {
  it('passes an ordinary message', () => {
    expect(scanOutgoing('what is the travel limit?').findings).toEqual([]);
  });

  it('spots a private key', () => {
    const found = scanOutgoing('-----BEGIN RSA PRIVATE KEY-----\nabc');
    expect(found.findings[0].kind).toBe('private-key');
  });

  it('spots a bearer token', () => {
    expect(scanOutgoing('use Bearer abcdef1234567890').findings[0].kind).toBe('bearer-token');
  });

  it('spots a password in a connection string', () => {
    const found = scanOutgoing('postgres://ada:hunter2secret@db/app');
    expect(found.findings[0].kind).toBe('connection-string');
  });

  it('spots an assigned password', () => {
    expect(scanOutgoing('password = hunter2secret').findings[0].kind).toBe('password');
  });

  it('spots an api key', () => {
    expect(scanOutgoing('api_key: abcdef1234567890').findings[0].kind).toBe('api-key');
  });

  it('ignores an obvious placeholder', () => {
    // Warning about "password = changeme" teaches people to click through.
    expect(scanOutgoing('password = changeme').findings).toEqual([]);
  });

  it('ignores a password too short to be one', () => {
    expect(scanOutgoing('password = abc').findings).toEqual([]);
  });

  it('ignores a token too short to be one', () => {
    expect(scanOutgoing('bearer abc').findings).toEqual([]);
  });

  it('says which line it was on', () => {
    const found = scanOutgoing('hello\nthere\npassword = hunter2secret');
    expect(found.findings[0].line).toBe(3);
  });

  it('never repeats the secret back in the excerpt', () => {
    const found = scanOutgoing('password = hunter2secret');
    expect(found.excerptsContainSecret).toBe(false);
  });

  it('finds more than one', () => {
    const found = scanOutgoing('bearer abcdef1234567890\napi_key: abcdef1234567890');
    expect(found.findings).toHaveLength(2);
  });

  it('leaves sending to the person, never blocking it', () => {
    // A composer that refuses to send loses the message.
    expect(scanOutgoing('password = hunter2secret').safeToSend).toBe(true);
  });
});
