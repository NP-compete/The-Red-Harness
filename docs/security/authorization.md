# Who may do what

## One decision point

Authorization is decided by the policy engine, not here. This
side supplies attributes — who is asking, what they are asking
about, what they want to do — and the engine answers.

Per-resource authorization for documents, skills, threads and
tools is not built yet. When it is, there are exactly two
acceptable shapes:

1. A resource model here, with the policy engine still the
   decision point: richer input, one decision.
2. Policy extended to cover those resources directly, with this
   side passing identifiers only.

A third shape — a role-and-permission table here, answering the
question itself — is not acceptable. Not because it would be
written badly, but because it would be *second*. Two systems
that both answer "may they" disagree eventually, and the
disagreement is found by somebody having access they should not
have.

Choosing between 1 and 2 is a conversation with whoever owns the
policy, and it has not happened. Nothing here should pre-empt it.

## The guard

`tests/unit/security/test_no_parallel_rbac.py` fails if a
role-to-permission table appears, or if one of the three
modules below becomes reachable.

### Three modules that already decide, and are not called

| Module | What it holds |
|---|---|
| `security/scope_check.py` | `ADMIN_ROLES`, and read/write/delete decisions |
| `security/impersonation.py` | `ALLOWED_ROLES` |
| `security/audit_query.py` | `WIDE_ROLES`, `DETAIL_ROLES` |

Nothing imports any of them. That is the only reason they are
tolerable: an unreachable decision point is not deciding
anything. The guard is on **reachability**, not existence —
wiring one up is what turns this deployment into two
authorization systems, so that is what fails the build.

If one of these is the beginning of shape 1, finish the
conversation first and feed its attributes to the engine rather
than letting it answer.

## What this does not forbid

Asking who somebody is. Gating an operator page on a coarse
role, as `PRIVILEGED_ROLES` does for analytics, admin and
documents. A resource knowing who owns it — ownership is an
attribute of the thing, not a decision about it.

## When somebody leaves

`plan_departure` describes the work and `carry_out` does it.
They are separate because the description is worth reading
before anything is revoked.

| | |
|---|---|
| Revoked | every connection they had authorised |
| Stopped | unattended work running on their grant, with a reason naming them |
| Removed | their own collections |
| **Kept** | **anything they put in a team, and the shared corpus** |

The last row is the one to be careful about. What somebody
put in a team was never theirs alone, and taking it on the
way out removes a colleague's runbook because its author
changed jobs.

Every step is attempted even when one fails. Stopping at the
first failure would leave the rest of somebody's access in
place because one unrelated thing was unreachable — and a
half-done departure is worse than either end state, since
some credentials live on and nobody knows which. What did not
happen is returned, named, so it can be finished by hand.
