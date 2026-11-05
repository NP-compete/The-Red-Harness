# Configuration compatibility

A deployment's configuration lives in its own repository, and is
edited by people who are not reading this one. The field at the top
of `runtime/agent.yaml` is how the two stay honest with each other:

```yaml
schema_version: 3
```

## What a build accepts

A build reads the current version and the one before it. The window
is declared in `services/agent/src/agent/config/schema_version.py`:
`CURRENT`, and `OLDEST_SUPPORTED` one below it.

| The tree says | What happens |
|---|---|
| The current version | Loads. |
| The previous version | Loads, and the configuration report says it is the oldest still supported. |
| Nothing at all | Loads, read as the oldest supported version, and reported. No tree written before the field existed should fail on the rollout that introduced it. |
| Anything older | Refused at startup, naming the version to migrate to. |
| Anything newer | Refused at startup, naming the upgrade. The alternative is a pod quietly ignoring every field it does not recognise. |
| Something that is not a whole number | Refused. Reading `three` as `3` is how a typo becomes a tree nobody can tell the version of. |

A pod publishes both halves on `GET /admin/config` under `schema`,
and the Settings → Developers tab shows them beside the build
version. Either number alone is unreadable: a tree declaring version
2 starts on one image and is refused by the next.

## What needs a version bump

| Change | Bump | Allowed |
|---|---|---|
| New optional field with a safe default | No | Yes |
| New required field | Yes | Only with a default that preserves the previous behaviour |
| Renamed field | Yes | Only with the old name still accepted for one version |
| Removed field | Yes | Only after a version of deprecation warnings |
| Changed default | Yes | Only when the old default is unsafe, and the migration note says so |
| Changed meaning of an existing value | Yes | Avoid. No test can catch this one: every tree still loads and every tree now means something else. |

## What a migration note contains

One per version, in this file, under a heading naming the pair of
versions. Four things, and a note missing any of them is not a
migration note:

1. **Every field that moved, by its old and new name.** Not "the
   approval section was reorganised".
2. **What happens to a tree that is not migrated** — refused, or
   loaded with a changed default.
3. **The mechanical part**, as a command somebody can run.
4. **The part that is not mechanical**, said plainly. A changed
   default is a decision, not a rename, and the note is where
   somebody is told they have one to make.

## Warnings, before the removal

A setting due to go is warned about by the pod that is running it,
once per process, naming the version it goes in and what to use
instead. It appears in the configuration report and in Settings →
Developers, not only in the log, because the log line is in a pod
that may since have restarted.

The registry is `services/agent/src/agent/config/deprecations.py`. An
entry goes in when a field is renamed, and comes out in the version
named — a field removed without a version of this is a change the
policy above does not allow.

Already registered: a config file still at its pre-rename path. The
resolver keeps reading it, which is exactly why the deployment has
no reason to notice.

## Migrating

```sh
make migrate-config DIR=/path/to/tree ARGS=--dry-run   # look first
make migrate-config DIR=/path/to/tree
```

One tree, one version forward. It raises `schema_version`, applies
the renames for that version, and prints anything that is *not*
mechanical rather than deciding it — a changed default is a
decision, and a script that makes it quietly is worse than one that
refuses.

It edits the file line by line rather than parsing and rewriting
it. Round-tripping `agent.yaml` through a YAML writer reformats it
and drops every comment, and for that file the comments are the
documentation a deployment reads.

It refuses a tree already at the current version and a tree from
the future, and writes nothing when it refuses.

## Before a rollout

Point the candidate image at your own trees. The check ships;
the corpus does not, because it is yours.

```sh
make validate-configs DIR=/path/to/your/agent-configs
```

Every directory under `DIR` holding an `agent.yaml` — at
`runtime/agent.yaml` or at the top level — is loaded against this
build's models. One line per tree, the reason under any that failed,
and a non-zero exit if any did, so a pipeline step fails rather than
printing something nobody reads. Every tree is checked, not just as
far as the first failure.

Run it against the image you are about to deploy, not the one you
are running. The point is to find the trees the *new* build refuses.

A directory holding no trees at all is a failure too: a wrong path
that exits zero is a pipeline step that checked nothing.

## The corpus in this repository

`tests/fixtures/configs/` holds enough shapes to catch a careless
change without reaching outside this repository:

| Tree | Shape |
|---|---|
| `shipped` | The worked example, by symlink rather than copy — two copies of one file drift. |
| `minimal` | The least a tree can contain and still load. |
| `legacy-flat` | `agent.yaml` at the top level, the layout the resolver still reads. |
| `every-block` | Every optional file present, against a plain main file. |
| `oldest-supported` | Deliberately at the old end of the window. |

All five load in CI. A change that breaks one of them is a change
that breaks somebody's tree.
