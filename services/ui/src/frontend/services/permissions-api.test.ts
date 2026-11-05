import { afterEach, describe, expect, it, vi } from 'vitest';

import { getApprovalPolicy } from './permissions-api';

function answers(status: number, body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    }),
  );
}

const PAYLOAD = {
  effects: 'live',
  dry_run: false,
  filesystem: {
    rules: [
      { operations: ['ls', 'read'], paths: ['docs/**'], mode: 'allow' },
      { operations: ['edit', 'write'], paths: ['*.py', 'config/**'], mode: 'deny' },
    ],
  },
  approval: {
    enabled: true,
    default_decision: 'ask',
    policies: [
      {
        tools: ['ls', 'read_file'],
        decision: 'allow',
        risk: 'low',
        reason: 'Read-only inspection of the workspace',
      },
      {
        tools: ['execute'],
        decision: 'ask',
        risk: 'high',
        reason: 'Runs arbitrary commands in the agent sandbox',
      },
    ],
  },
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('getApprovalPolicy', () => {
  it('reports what runs without asking and what does not', async () => {
    answers(200, PAYLOAD);
    const policy = await getApprovalPolicy();
    expect(policy?.rules.map((rule) => rule.decision)).toEqual(['allow', 'ask']);
  });

  it('keeps the reason each rule gives', async () => {
    answers(200, PAYLOAD);
    const policy = await getApprovalPolicy();
    expect(policy?.rules[1].reason).toBe('Runs arbitrary commands in the agent sandbox');
  });

  it('reports what happens to a tool no rule names', async () => {
    answers(200, PAYLOAD);
    expect((await getApprovalPolicy())?.otherwise).toBe('ask');
  });

  it('says when approval is switched off entirely', async () => {
    answers(200, { approval: { enabled: false, default_decision: 'allow', policies: [] } });
    expect((await getApprovalPolicy())?.enabled).toBe(false);
  });

  it('puts the ones that stop and ask first', async () => {
    answers(200, PAYLOAD);
    const policy = await getApprovalPolicy();
    expect(policy?.rules[0].decision).toEqual('allow');
  });

  it('knows nothing when the agent cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await getApprovalPolicy()).toBeNull();
  });

  it('knows nothing when the answer has no policy in it', async () => {
    answers(200, {});
    expect(await getApprovalPolicy()).toBeNull();
  });

  it('skips a rule that names no tools', async () => {
    answers(200, {
      approval: { enabled: true, default_decision: 'ask', policies: [{ decision: 'allow' }] },
    });
    expect((await getApprovalPolicy())?.rules).toEqual([]);
  });
});

describe('what the agent may touch', () => {
  it('reports where it may read', async () => {
    answers(200, PAYLOAD);
    const policy = await getApprovalPolicy();
    expect(policy?.workspace[0]).toMatchObject({
      operations: ['ls', 'read'],
      paths: ['docs/**'],
      allowed: true,
    });
  });

  it('reports where it may not write', async () => {
    answers(200, PAYLOAD);
    const policy = await getApprovalPolicy();
    expect(policy?.workspace[1].allowed).toBe(false);
  });

  it('says whether what it does is real', async () => {
    answers(200, PAYLOAD);
    expect((await getApprovalPolicy())?.live).toBe(true);
  });

  it('knows a dry run changes nothing outside the conversation', async () => {
    answers(200, { ...PAYLOAD, dry_run: true });
    expect((await getApprovalPolicy())?.live).toBe(false);
  });

  it('copes with an agent that lists no workspace rules', async () => {
    answers(200, { approval: PAYLOAD.approval });
    expect((await getApprovalPolicy())?.workspace).toEqual([]);
  });

  it('skips a rule naming no paths', async () => {
    answers(200, { ...PAYLOAD, filesystem: { rules: [{ operations: ['read'] }] } });
    expect((await getApprovalPolicy())?.workspace).toEqual([]);
  });
});
