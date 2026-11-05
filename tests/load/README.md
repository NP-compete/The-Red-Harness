# Load tests

k6, against a running stack. 80 heavy users across every feature,
or one feature on its own.

```sh
make load                        # the 80-user mix
make load FEATURE=chat           # one journey, same concurrency
make load VUS=10 DURATION=1m     # a sanity pass
make load-list                   # what you can run alone
```

Running a feature alone is how you tell *the system is slow under
load* from *this endpoint is slow*: the mixed run gives the first
answer and a single scenario gives the second.

## What a heavy user does

`lib/journeys.js` holds one function per feature. The mix in
`all-features.js` is weighted like a working day rather than
evenly — people read the sidebar constantly and open analytics
occasionally — because an even split spends most of the run
measuring the page nobody opens.

Every path was taken from `/openapi.json`. A 404 under load is a
green test measuring a wrong URL.

## Three things that will mislead you

**Chat is off by default.** A turn costs a model call, and 80 of
them in parallel against a real provider measures that provider's
rate limiter and produces a bill. `make load-chat` turns it on.
Either way the run prints which model answered, so a result can
never be quietly attributed to the wrong one.

**The UI's rate limiter is a ceiling on the whole run.** 80 users
from one machine are *one client* to it. Spoofing
`X-Forwarded-For` per VU does not help: the ingress appends the
real peer and the BFF keys on that, which its own
`remoteAddress` log confirms. So UI 429s are counted on their own
`rate_limited` metric rather than hidden or treated as failures,
and `features/rate-limit.js` asserts the limiter on purpose.

**A 404 can mean "switched off here".** `knowledge/documents`
returns one when the capability is not enabled. Those are counted
as `feature_not_offered`, so a run can say how much of the surface
it actually reached instead of reporting a tidy pass over half of
it.

## Thresholds

Read p95 under 800ms, p99 under 2s; writes p95 under 1.5s; checks
above 99%; non-2xx below 1%. Chat has its own `chat_turn_ms`
trend and is excluded from those percentiles — one 20-second
model call would otherwise drag the figure for every list
endpoint with it.

Expected answers are declared per call, not by loosening the
threshold: the limiter's 429 and a switched-off feature's 404 are
expected, and every other non-2xx is still a failure.

## Measured

80 VUs, 45s, chat off, against Kind:

| | |
|---|---|
| checks | 13,633, 100% |
| requests | 9,656 at 106/s |
| read p95 / p99 | 39ms / 75ms |
| write p95 | 48ms |
| UI 429s | 450, the limiter |

The agent API is not the bottleneck at this concurrency. The
first limit you meet is the BFF's rate limiter, and it is a
configured one.

## Not to be confused with

`scripts/bench/` measures answer *quality* against task suites.
This measures *capacity*. A green run here says nothing about
whether the answers were any good.
