# What a month cost, and who pays

Token counts answer "how much work was that". Nobody settles an
invoice in tokens and nobody allocates them to a team, so there is a
second figure: money against a payer, for a period.

## It is not the same thing as the caps

Two numbers that look alike and are not.

The **counters** decide whether a run may start. A run is counted
against every budget that has to refuse it — the person *and* their
team, both — because either of them reaching its cap must stop the
next run.

The **ledger** is the bill. A cost is paid once, by one payer.
Totalling the counters would charge the company twice for the same
run, which is why these are kept apart rather than derived from one
another.

## Who pays

In order, first match wins:

| If the run… | …the payer is |
|---|---|
| names a project | that project |
| was run by somebody in a budgeted team | that team |
| says it was unattended | `platform` |
| anything else | the person who ran it |

Who *ran* it is recorded either way. "Who spent this" is the next
question after the total, and the payer does not answer it.

## Unattended work

A run started by a schedule carries a person's identity only because
something had to be put there. Billing them is wrong twice over: they
did not ask for it, and a standing cost of running the place shows up
as one colleague spending suspiciously much.

A caller that knows it is unattended says so in the run's metadata:

```json
{
  "metadata": {
    "user_id": "alice",
    "started_by": "schedule",
    "project": "atlas"
  }
}
```

Both fields are optional and both are read from `metadata` or
`configurable`, the same two places the caller's identity comes from.
Anything other than a value this recognises is read as a person —
unknown means today's behaviour, and a run wrongly treated as
unattended stops being charged to anybody who would notice.

The counters are unaffected: a schedule running away under somebody's
name still counts against them and is still stopped. The brake is on
an identity's rate of spending, whoever ends up paying.

## Reading it

`GET /costs/chargeback?month=YYYY-MM`, largest payer first. Without a
month it answers for the current one. A month that is not a month is
refused rather than quietly read as this one — somebody exporting the
wrong period and not being told is how a wrong invoice goes out.

Each row carries a run count beside the money. A total with nothing
behind it cannot be checked: twice the spend on half the runs is the
finding, and the total alone hides it.

The rate card version travels with the figures. A number with no
version against it cannot be checked against the contract that priced
it, and re-pricing history so that it checks out is how a record stops
being a record.

A month is kept for 120 days. Finance reconciles after a month closes,
not during it, so an expiry sized for the month itself would lose the
figure on the day the invoice is raised.

## When it is empty

A ledger that cannot be written never costs an answer — the run has
already happened and the model has already been paid for, so a lost
line is logged and swallowed. A ledger that cannot be read answers
empty rather than failing: an empty invoice is wrong, but it is
visibly wrong, where a page that will not load says nothing at all.
