# Built, tested, and reached by nothing

A module with tests and no callers passes every check and does
nothing. It is worse than missing code, because missing code is
visible: here the test count goes up, coverage looks fine, and the
capability does not exist.


**How many, and which ones, is computed rather than copied.**

```sh
make unreachable          # the live list, grouped by directory
```

`tests/unit/test_unreachable_modules.py` is the source of truth:
it parses every import in the tree, pins the count as a ratchet
that may fall and never rise, and carries a dated log of what
changed and why. `tests/unit/security/test_controls_are_reachable.py`
does the same for `src/security/` alone, and additionally fails
when the count drops more than five below its ceiling — a ceiling
that has stopped biting is no better than none.

This page used to open with a total and then hand-copy all 170
paths. By the time anybody read it again, eight of those modules
had been deleted and the total was wrong by fourteen. A page whose
subject is code that is not what it appears to be should not
itself be a list of files that no longer exist, so the list is
gone and the command stays.

## Why this list exists rather than a deletion

Some of these are staged work waiting on a decision, and deleting
somebody else's half-finished capability is not a call to make from
a test count. What the ratchet buys is that the pile stops growing
while those decisions are taken one at a time.

## The ones already dealt with

Found by accident, one at a time, before the sweep existed:

- a schema-version check nothing called
- a rate limiter nothing consulted
- an inbound config model nothing read
- a retrieval store nothing wrote to
- a departure plan nothing carried out
- a thread lease nothing claimed
- a hand-off plan nothing could ask for
- a tool preflight with nothing to feed it

Each looked finished. That is the point.


## How to read the pile

Not module by module. The question that decides each one is
**"is this a capability the product lacks, or a second answer to
a question the live path already decides?"** — and the fastest
first cut is whether a *reachable* module shares a name token
with it. That is triage and nothing more: of the twelve read
most recently, six were duplicates and six were not. One
namesake was the wrong module entirely, two were a different
subject, one belonged to an unwired feature rather than being a
copy of anything, and one looked like a missing refusal until
the configuration beside the setting turned out to explain why
nobody should refuse there.

Three outcomes, in rough order of how cheap they are:

- **A second answer to a live question** — delete it, naming the
  module that already answers. `fair_share`, `admission`,
  `pii_masking`, `graceful_shutdown`, `inflight_gauge`, `share`,
  `token_refresh`, `spend_decision` and `audit_alerts` went this
  way.
- **An unwired feature** — several modules that are one
  capability, not several duplicates. Signing, verifying and key
  rotation are the clearest: deleting them one at a time
  dismantles something nobody decided to drop.
- **A product decision** — `break_glass`, `legal_hold`,
  `residency`, `impersonation`, `session_revocation`, `sandbox`.
  Deleting these is a call about what the product is for, and
  the right move is to take them as a few decisions rather than
  dozens.

The full reasoning, module by module where it has been done,
is in the NFR-SEC section of the PRD.

## One with a named blocker

`src/agent/compaction.py` is ready and cannot be wired yet.

It decides which part of a long conversation to summarise, and
it refuses to touch three things: a pending approval, a skill,
and anything untrusted. The graph's messages carry no
equivalent of those three flags, so mapping one onto the other
would mean guessing — and guessing wrong summarises away the
question somebody is about to answer, or launders an untrusted
tool result into something the agent believes.

`can_be_wired()` returns that reason rather than a middleware
that runs and silently decides all three are false. The
prerequisite is those flags existing on the graph's messages;
until then the interface's compaction marker cannot appear,
because nothing compacts.


## The count jumped from 113 to 170, and nothing regressed

Every number before this was taken with a check that asked whether a
module's filename appeared anywhere in another file. That is true of
far more than an import: a configuration field with the same name, a
function named after it, a comment, a log line. Fifty-seven modules
nothing imports were being counted as wired — including a second,
unused implementation of tool shortlisting whose name collides with a
configuration field, which is how it stayed hidden while its sibling
carried a bug.

The check now counts imports, parsed rather than matched as text. The
number is larger and finally means what it says.

Two consequences worth stating plainly. The earlier numbers in the log
above are not comparable with this one, and the drops recorded there
were real but measured against an inflated baseline. And this check is
one I quoted repeatedly while it was wrong.

Three entry points are exempt, by path rather than by filename: the
server app, the worker entrypoint and the console script. None is
imported by anything here and none is an orphan. `main.py` is a common
name, so exempting it by filename would hide a real orphan the day
somebody adds one.

## Four of them claimed to be doing a job

With the count honest, the server package turned out to hold four
modules whose opening paragraph states a role in the running system:
error-handling wrappers "used by the graph builder", conversion helpers
for "when the agent runs via `aegra dev`", a state schema "used when
the agent runs on LangGraph Platform", and serialization "for
persistence, API responses, and cross-service communication".

Nothing imports any of them.

That is worse than plain dead code. Dead code gets found and deleted; a
module whose first paragraph says it is load-bearing gets believed.
Somebody debugging a conversion problem reads `converters.py`, finds
the logic plausible, and goes looking elsewhere for the bug — the file
was never in the path. The retry wrappers are the sharper case: a
reader concludes failures are being retried at the integration
boundary, and they are not.

Each now says so, under the description rather than instead of it — a
reader deciding whether to wire one up still needs to know what it
would do. A test holds both halves: that the module is still dormant,
and that it still admits it. Wire one up and the first half fails,
which is the prompt to take the note out.

The dormancy itself is not fixed here. Whether these should be wired or
deleted is a decision about the server's design, not a tidy-up.
