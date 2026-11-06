# Declared checks (E22)

One YAML file per check. A check says which group it belongs to and
**what decision it informs** — that last field is required, because a
score nobody acts on is a number that gets watched forever.

    name:     unique, and the key a score is recorded under
    group:    safety | accuracy | privacy | tool_correctness | regression
    decides:  what a human does differently when this fails
    judge:    what scores it (omit when the check is asserted, not judged)
    needs:    MCP integrations the cases cannot be answered without
    dataset:  path under the config root
    cases:    which case ids in that dataset are about this check

These files are part of the config tree, so they are visible on the
config surface and a deployment can add one without a code change.

`needs:` is checked against `/mcp/<name>/status` on the agent being
scored, and a check whose integration is down is reported as
**skipped, naming it** — not failed. An agent with no Google
Workspace answers "I cannot answer this without Google Workspace",
which fails every assertion about the briefing it was meant to
write: a red that is the measurement's own fault, and the kind that
teaches people to ignore a suite. Declare it only where the *case*
needs the integration. An answer the agent gives anyway — a refusal
on policy, say — is behaviour worth scoring, and skipping it would
hide a real finding.

A check is only written where a dataset exists that measures what the
check claims. Pointing one at a whole dataset makes it score
assertions that are not about it and report the result under a name
that is not true of it — which is worse than having no check, because
the group then reads as covered.
