# Two things called documents

They are not the same feature and should not be merged without
deciding which one wins. Both exist on purpose.

| | `/documents` | `/knowledge/documents` |
|---|---|---|
| Whose | the deployment's, one shared volume | one person's |
| Who may write | a privileged role only | the person themself |
| Capacity | one total for everyone | a quota each |
| How the agent reads it | filesystem tools, at a path | scope-aware retrieval |
| Where it lives | a mounted volume | the document library |

The shared volume is a place to put files the agent can read as
files — the model's route is read-only and human writes go
through a privileged door, so the two never share a path.

The library is for retrieval. A document there is reachable
through a **scope**, and the scope is part of the query:

| Scope | Lifetime | Visible to |
|---|---|---|
| `session` | the thread | its participants |
| `user` | until removed | the owner |
| `team` | until removed | the group it belongs to |
| `agent` | until removed | everyone using the agent |

Team membership comes from the identity provider's groups. It is
never a list kept here: a local member table is a second place
deciding who is in what, and the first time it disagrees with the
directory somebody keeps access they lost weeks ago. The store
matches the groups the caller arrived with and looks nothing up —
asserted by a test that fails if it ever starts to.

Agent scope is configuration. The corpus lives at
`config/agent/knowledge/` and is synced from the tree at
startup. A folder per team under `knowledge/teams/<team>/`
belongs to that team and nobody else:

```
knowledge/
  handbook.md              everyone using this agent
  teams/platform/runbook.md   the platform group only
  teams/finance/ledger.md     the finance group only
```

Which group gets what is the configuration author's decision,
and the same kind they already make about the shared corpus.
Who is *in* the group is not theirs to decide — that comes from
the directory. A file loose directly inside `teams/` belongs to
no team, so it is skipped and said rather than guessed at.

The sync ingests at startup, reindexes on change, and
**removes a document deleted from the tree**, because otherwise the corpus is
whatever has ever been in it.

There is deliberately no interface for creating a collection. A
taxonomy that nothing queries is how the previous version of
this went wrong: it offered named collections while retrieval
ignored them and searched everything the owner had.

## An attachment is a session document

A file attached to a conversation is reachable two ways, and
they are the same file:

- through the filesystem tools, at its path, as before;
- through retrieval, in `session` scope, from the moment it is
  attached.

It was only the first of those for a long time, which meant
"what did that document say" worked only if the model thought
to go and read the file.

Taking the copy never fails an upload. By the time it runs the
file is written and the person is waiting — a library that
cannot take a copy is not a reason to lose their upload, so
every failure there is logged and swallowed.

A second upload of the same file replaces the first rather than
matching twice and being cited twice. Deleting the conversation
takes its attachments out of the library with it.

## One name for a person

A document is written by a page and found by the agent during a
conversation. That only works while both sides call the person the
same thing.

They did not. A run resolves `metadata.user_id` — the signed-in
username the interface sends. The pages asked for the token's `sub`,
which is a UUID with authentication on and a fixed stand-in with it
off. So a document somebody uploaded was invisible to the agent in the
very conversation they uploaded it for.

Nothing failed. The search answered "nothing found", which is a
sentence it is supposed to be able to say, so there was nothing to
notice. The same drift had already cost an allowance page, which read
a spend counter under one name that runs wrote under another and
reported nothing spent, for ever, to somebody about to be refused.

Both now use the helper that already answered with the id runs use:
`X-User-ID` with authentication off, the verified `preferred_username`
with it on, and a 403 when a header claims to be somebody the token is
not. A test pins each page to it.

Two more places had the same fault, found by looking rather than by
anybody reporting it — which is the point, because none of them can be
reported. The directory matches people by `uid=<username>`, so asking
it about a subject finds nobody, and "nobody" is indistinguishable from
"in no teams":

  - the document page resolved team membership that way, so every team
    corpus quietly disappeared for everyone;
  - the inbound door did too, so a configured team cap applied to
    nobody.

And the door keyed its per-person spend counter on the subject while
runs wrote under the username, so it asked what somebody had spent,
got nothing, and admitted every run. A cap that always answers "plenty
left" is worse than no cap: somebody configured it and believes they
are protected.

A sweep now checks every function that asks the directory, per
function rather than per file — a module may legitimately use the
subject for something that is not a directory lookup, and a
file-level check calls that a fault, which is a check people learn to
silence. It asserts it found at least three callers, because the first
version of the sweep looked in the wrong directory, matched nothing,
and passed.

The sweep is also shown to fail. Three planted sources — one asking
with the subject, one asking with the username, and one module doing
both for different reasons — prove the walk flags what it claims and
leaves alone what it should. A green sweep on its own says nothing: a
walk that quietly matches no functions looks exactly like a codebase
that gets this right everywhere.

The planted sources and the real sweep call the same walk. Writing the
check twice so the tests could reach it would have been the very fault
this section is about.
