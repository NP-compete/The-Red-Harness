# `harness`

Generated from the parser by `make cli-docs`. Edit the
command, not this file — a page kept by hand is wrong the
first time somebody adds a flag.

Talk to an agent, and find out why it is not working.

```
exit codes: 0 it worked, 1 it did not, 2 used wrongly, 3 it is waiting for a decision, 4 it does not know who you are, 5 it worked but something is missing
```

## `harness acp`

| | |
|---|---|
| `--ui-dir` | where the interface is built |

## `harness agent`

| | |
|---|---|
| `--ui-dir` | where the interface is built |

## `harness all`

| | |
|---|---|
| `--ui-dir` | where the interface is built |

## `harness ask`

| | |
|---|---|
| `question` | what to ask |
| `--approve-all` | answer every approval with yes, without asking. Each one is printed; an approval gate nobody sees open is not a gate |
| `--follow` | print the answer as it arrives, rather than when it is finished |
| `--json` | machine-readable output |

## `harness completion`

| | |
|---|---|
| `shell` |  |

## `harness config`

### `harness config diff`

| | |
|---|---|
| `--json` | machine-readable output |

### `harness config list`

| | |
|---|---|
| `--json` | machine-readable output |

### `harness config render`

| | |
|---|---|
| `--json` | machine-readable output |
| `--out` | a directory to write into |

### `harness config set`

| | |
|---|---|
| `--json` | machine-readable output |
| `path` |  |
| `--from` | where the new text comes from; '-' is stdin, the default |
| `--force` | write without the version it was read at, overwriting whatever is there |

### `harness config show`

| | |
|---|---|
| `--json` | machine-readable output |
| `path` |  |

## `harness docs`

Takes no arguments.

## `harness doctor`

| | |
|---|---|
| `--json` | machine-readable output |

## `harness eval`

### `harness eval list`

| | |
|---|---|
| `--json` | machine-readable output |

### `harness eval run`

| | |
|---|---|
| `--json` | machine-readable output |
| `check` |  |

### `harness eval usage`

| | |
|---|---|
| `--json` | machine-readable output |

## `harness eval-worker`

| | |
|---|---|
| `--ui-dir` | where the interface is built |

## `harness mcp`

### `harness mcp connect`

| | |
|---|---|
| `--json` | machine-readable output |
| `name` |  |
| `--open` | open the authorize URL in a browser |
| `--wait` | poll until it connects, then say who as |

### `harness mcp disconnect`

| | |
|---|---|
| `--json` | machine-readable output |
| `name` |  |

### `harness mcp list`

| | |
|---|---|
| `--json` | machine-readable output |

### `harness mcp status`

| | |
|---|---|
| `--json` | machine-readable output |
| `name` |  |

## `harness observe`

| | |
|---|---|
| `--json` | machine-readable output |
| `--limit` | conversations to read |
| `--since` | ignore anything older (ISO date) |
| `--propose` | also say what could be changed, as a diff somebody reviews |
| `--max` | how many proposals at most |

## `harness opa`

| | |
|---|---|
| `--ui-dir` | where the interface is built |

## `harness propose`

| | |
|---|---|
| `--json` | machine-readable output |
| `--before` | settings as they are |
| `--after` | settings as proposed |

## `harness resume`

| | |
|---|---|
| `--json` | machine-readable output |
| `thread_id` |  |
| `decision` |  |
| `--message` | why, for a rejection |

## `harness run`

### `harness run attach`

| | |
|---|---|
| `--json` | machine-readable output |
| `thread_id` |  |
| `run_id` |  |
| `--follow` | watch the rest of it arrive |

### `harness run cancel`

| | |
|---|---|
| `--json` | machine-readable output |
| `thread_id` |  |
| `run_id` |  |

### `harness run list`

| | |
|---|---|
| `--json` | machine-readable output |
| `thread_id` |  |

### `harness run show`

| | |
|---|---|
| `--json` | machine-readable output |
| `thread_id` |  |
| `run_id` |  |

## `harness skill`

### `harness skill list`

| | |
|---|---|
| `--json` | machine-readable output |

## `harness thread`

### `harness thread fork`

| | |
|---|---|
| `--json` | machine-readable output |
| `thread_id` |  |

### `harness thread list`

| | |
|---|---|
| `--json` | machine-readable output |

### `harness thread rm`

| | |
|---|---|
| `--json` | machine-readable output |
| `thread_id` |  |

### `harness thread show`

| | |
|---|---|
| `--json` | machine-readable output |
| `thread_id` |  |

## `harness ui`

| | |
|---|---|
| `--ui-dir` | where the interface is built |

## `harness worker`

| | |
|---|---|
| `--ui-dir` | where the interface is built |
