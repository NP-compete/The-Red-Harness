# Guardrails Security Risk Register

## What is in place

### Granite Guardian (IBM) — LangChain callback
Registered process-globally via `register_configure_hook`. Fires on every LangChain
LLM call in the process, including in-process subagents.

| Hook | What it checks | Action |
|---|---|---|
| `on_chat_model_start` | Last human message — safety + injection | Blocks if unsafe (raises `InputContentSafetyError`) |
| `on_tool_start` | Tool call arguments (sensitive keys redacted) | Blocks if unsafe (raises `ToolContentSafetyError`) |
| `on_tool_end` | Tool result | Audit log only — result safety is handled by `GuardianToolProxy` |
| `on_llm_end` | LLM response | Logs always; always blocks unsafe output |
| `on_tool_error` | Tool execution errors | Logs only |

Content deduplication: the handler SHA-256 hashes each scanned string and skips
re-scanning the same human message on repeat LLM rounds within an agentic loop.

### GuardianToolProxy — per-tool async proxy
`wrap_tools()` in `services/agent/src/guardrails/tool_proxy.py` replaces every tool
in the agent's tool list with a `GuardianToolProxy` when `GUARDIAN_API_BASE` is set.
The proxy runs three phases on every `ainvoke`:

1. **Pre-check args** — `check_safety(arg_text[:500])` before the inner tool executes.
   Unsafe: returns a `BLOCKED_INPUT` `ToolMessage`; inner tool is never called.
2. **Execute inner tool** — exceptions are caught and returned as `ToolMessage(status="error")`
   so other tools in a parallel batch are unaffected.
3. **Post-check result** — `check_safety` then `check_injection` on the result
   (first 500 chars). Unsafe: replaces the `ToolMessage`/`Command` content with
   `BLOCKED_RESULT` and signals `_safety_ctx["blocked"] = True`.

### SafetyAwareRunnable — agentic-loop circuit breaker
`services/agent/aegra/safety.py` wraps the compiled graph (`outermost=True`) and every
in-process subagent runnable (`outermost=False`).

- Injects a shared `_safety_ctx` dict into LangGraph config so proxies can signal
  blocks back to the runnable.
- **`astream_events`**: buffers AI output chunks; monitors `on_tool_end` events for
  the `BLOCKED_RESULT` sentinel. When the last in-flight tool in a parallel batch
  completes and one was blocked, it breaks the stream before the orchestrator's
  next LLM call — preventing a retry loop.
- **`ainvoke`**: overrides the final `AIMessage` with `_TOOL_SAFETY_REFUSAL` if any
  tool block was signalled, ensuring a consistent user-facing refusal regardless of
  what the LLM generated.
- Catches `ContentSafetyError` / `InputContentSafetyError` / `ToolContentSafetyError`
  at the outermost boundary and converts them to a clean refusal message rather than
  an unhandled exception.

### AuditMiddleware — structured platform audit trail
`services/agent/src/audit/middleware.py` (added via `build_middleware_list`) emits
structured JSON audit events to stdout for:

| Event type | Trigger | Key details emitted |
|---|---|---|
| `llm_call` | Every model invocation (sync + async) | model, message_count, latency_ms, status |
| `mcp_tool_call` | Tool in the agent's MCP tool name set | tool, args_keys, latency_ms, status |
| `memory_write` | `edit_file`/`write_file` under `/memories/` | path, latency_ms, status |
| `subagent_delegation` | `task` tool call | delegated_subagent, latency_ms, status |

The emitter scrubs sensitive keys recursively (password, token, api_key, secret,
auth, cookie, credentials, etc.) before serialising. A local ring buffer retries
events that fail to emit due to transient I/O errors.

### Memory write protection
`PersonalizationRepository.create_memory()` and `upsert_rule()` run a Guardian
check before writing to Postgres. Unsafe content is rejected and never stored.

### MCP tool abuse visibility
Every tool call is audit-logged via `GraniteGuardianCallbackHandler.on_tool_start`
(sanitized inputs) and `AuditMiddleware` (args keys, latency). Circuit breaker trips
after 5 MCP server failures. `server_names` filtering ensures agents only connect to
their declared MCP servers.

### Human-in-the-loop (HITL) — tool approval interrupts
`services/agent/src/agent/config/hitl.py` builds `interrupt_on` predicates for
`create_deep_agent`. When enabled, the LangGraph graph pauses before executing
named tools and waits for human approval before resuming.

### CI / supply chain
- Trivy scans container image before push to GHCR; CRITICAL severity fails the build.
- Gitleaks runs in pre-commit on every local commit.
- GitHub Secret Scanning + Push Protection active at platform level.

---

## Remaining risks

### 1. AsyncSubAgent (remote pod) — Medium
**Threat:** Orchestrator delegates to a remote subagent pod via HTTP. Guardian
callback and `GuardianToolProxy` do not cross process boundaries.

**Mitigation in place:** `on_tool_start` Guardian check scans the outgoing
instruction payload before dispatch. `AuditMiddleware` emits a `subagent_delegation`
event for every `task` tool call.

**Residual gap:** The remote pod's own LLM calls and tool calls are only
protected if that pod is deployed with `GUARDIAN_API_BASE` set.

**Required action:** Enforce `GUARDIAN_API_BASE` + Guardian env vars on
every deployed agent pod. Treat this as a deployment standard, not optional.

---

### 2. Per-user tool access control — High
**Threat:** All users of the same agent share identical tool access. A low-privilege
user can invoke any tool the agent has configured.

**Mitigation in place:** OAuth/DCR enforcement at the MCP connection layer.
`server_names` filtering scopes tools to what the agent config declares.

**Residual gap:** No RBAC layer between user identity and tool invocation.

**Required action:** Add a user-role-to-tool mapping in `graph.py` between
`get_current_user()` and `get_mcp_tools()` — filter allowed tools by user role
before passing to `create_deep_agent()`.

---

### 3. Legacy memory records — Low
**Threat:** Memories written to Postgres before the Guardian write-guard was
added are not checked and may contain injection payloads.

**Mitigation in place:** New writes are blocked. Guardian `on_llm_end` flags
any exfiltration in output.

**Required action:** Run a one-off migration job:
```python
for memory in repo.list_all_memories():
    is_safe, _ = await check_safety(memory.content, context="memory")
    if not is_safe:
        await repo.delete_memory(memory.user_id, memory.id)
```

---

### 4. Subagent system prompt not validated at config load — Low
**Threat:** A tampered subagent config file could inject instructions into a
subagent's system prompt at startup.

**Mitigation in place:** Subagents loaded from `config/subagents/*.md` which
are version-controlled. Guardian fires on all in-process subagent LLM calls via
the global callback, and `SafetyAwareRunnable` wraps each subagent runnable.

**Residual gap:** No runtime validation of subagent system prompt content at
config load time.

**Required action:** Add a startup Guardian check over all subagent `body` fields
in `load_subagents()` before building subagent instances.

---

### 5. Encoded / obfuscated prompt injection — Low
**Threat:** Base64-encoded, Unicode-homoglyph, or multi-step injection chains
that Guardian's model does not classify as unsafe.

**Mitigation in place:** Guardian `check_safety` + `check_injection` now run at
two layers: user input (`on_chat_model_start`) and every tool result
(`GuardianToolProxy` post-check). Full content is scanned — no truncation.

**Residual gap:** Model-level limitation — no classifier is perfect. No
additional decoding / normalization pass before Guardian.

**Required action:** Add a pre-check normalization step (decode base64, strip
unicode overrides) before passing content to `check_safety()`.

---

### 6. Guardian API fail-open on outage — Medium
**Threat:** If the Guardian endpoint is unreachable (network partition, pod crash,
misconfiguration), every `check_safety` and `check_injection` call catches the
exception, logs a warning, and returns `(is_safe=True, "error")`. All guardrail
checks — user input, tool args, tool results, LLM output, and memory writes — silently
pass through for the duration of the outage.

**Mitigation in place:** Each failed check emits a `guardian_check_failed` warning
log with `exc_info=True`. The agent remains available and functional.

**Residual gap:** This is a deliberate availability-over-security tradeoff. A Guardian
outage is operationally invisible to users and produces only per-check warning logs.
There is no alerting, no circuit breaker, and no `GUARDIAN_FAIL_OPEN=false` mode
for deployments that require guardrails to be enforced even at the cost of availability.

**Required action:** Add a `GUARDIAN_FAIL_OPEN` setting (default `true` to preserve
current behaviour). When `false`, failed Guardian checks return `(is_safe=False)`
so requests are blocked during an outage. Add a monitoring alert on the
`guardian_check_failed` log event to detect outages promptly.

---

### 7. Audit log integrity — Low
**Threat:** Audit events are emitted to stdout only. A compromised container
runtime or log-scraping pipeline could drop or tamper with audit records without
detection.

**Mitigation in place:** `AuditEmitter` uses a local buffer to retry transient
I/O failures. Structured JSON format is compatible with standard log collectors
(Fluentd, Datadog, CloudWatch).

**Residual gap:** No tamper-evident storage, log signing, or SIEM forwarding
configured. Audit completeness relies entirely on the container log driver.

**Required action:** Route stdout audit events (`event=platform.audit`) to a
write-once audit store or forward to a SIEM. Add an alert for gaps in
`trace_id` sequence or missing `llm_call` events in active threads.

## The two body-size guards had a rule each

Two guards sit in front of every request body. One reads the
`Content-Length` a client declared and rejects early, before anything is
sent. The other counts bytes as they actually arrive, because a declared
length is a claim and a chunked request has none at all.

They disagreed. The declared guard gave upload routes six times the
global allowance — multipart framing around a file needs the headroom —
and the streaming guard had no such branch, so it held those same routes
to the global figure. With the shipped settings that is 60 MB against
10 MB.

An upload between the two passed the cheap check, was accepted, began
transferring, and was cut off part way through. Nothing oversized got
in — the stricter number wins — but the system advertised a size it
would not accept, and the 413 the other guard produces quotes a limit
nobody enforces.

Both now call one function. The rule had been written twice, which is
how it came to be two rules; a test asserts the two agree on every
upload path, on an ordinary path, and on an explicitly overridden one,
and that only one place in the file names the upload patterns.

The streaming guard also takes the headroom as a constructor argument
with the same default, so building the two with the same arguments gives
the same limits. Passing it to one and not the other is the next version
of this bug.

## An icon fetch followed redirects on its own

A server's icon address comes from configuration. The fetch checked it
started with `https://` and then handed it to a client with
`follow_redirects=True`, so the first address was checked and nothing
after it was. A 302 pointed the pod at an address inside the cluster
and the reply came back as long as it carried an image content type.

Configuration is more trusted than a model and still not trusted enough
for that. The host it names can be a content network that changes
hands, and *fetches whatever that domain says next* is a worse property
than anybody chose.

Each hop is now checked before it is followed, against a list holding
one entry: the host the configuration named. A path moving is what a
content network does; the domain moving is a question worth refusing.
Loops and long chains are refused too.

What this does **not** do is resolve the name and pin the connection to
the address that was checked. The document fetcher does, and this wants
the same treatment the day an icon comes from anywhere less deliberate
than a configuration file. A host that answers with a public address on
the first lookup and an internal one on the second is still reachable
here.

There is a second place that still follows redirects freely: OAuth
metadata discovery, where a resource and its issuer legitimately
redirect to one another. That one is a deliberate choice with a comment
explaining it, not an oversight, but it is the same shape and belongs
in the same conversation.

## A shared credential was invisible

Nearly every integration is reached with the identity of the person who
asked, so the far side sees who is acting and its own permissions
apply. One mode does not: a server configured with a shared key is
reached as the deployment, by everybody. Whatever that key can do,
every person using the agent can do through it.

That is a legitimate choice — some services have no per-person
credential to offer — but it was one line in a configuration file and
nothing said it out loud, so reviewing a deployment meant noticing an
absence rather than reading a statement.

Startup now names those servers and says what it means, rather than
restating the setting. A warning and not a refusal: it is a supported
mode, and refusing to start would take the decision away from the
deployment rather than show it to them. An unset mode is the
per-person default and is not warned about — treating it as shared
would warn about every server anybody ever configured, which is how a
warning becomes noise.

The shipped tree is silent: all eight configured servers carry the
caller's identity.

## What the security rules were checked against

Nine of the ten hold. Two did not and were fixed — the two body-size
guards disagreeing on upload paths, and the icon fetch following
redirects without revalidating each hop. Both are written up above.

The remainder were read rather than assumed:

- **Per-user authorization.** The default mode is the caller's own
  identity; a shared credential is an explicit per-server choice and is
  now named at startup.
- **Tokens at rest.** Sealed with a key the pod refuses to start
  without, with a message explaining why generating one would be worse
  than failing.
- **One permission model.** Policy decisions go to the policy engine;
  scope enforcement lives in the stores, which is data access rather
  than a second policy engine. The artifact store follows the same
  pattern the document store already does.
- **Hostile filenames.** Judged in decoded form, so `%2e%2e` and `..`
  are caught by one rule; control characters and backslashes refused.
- **Secrets in transit.** Outbound tool calls are scanned and refused
  by default, and the refusal names the kind rather than the value — a
  warning that repeats a secret has moved it rather than kept it back.
- **The content security policy.** Derived from configuration, so a
  new host is a setting rather than a second place to edit, with the
  scheme checked before anything is added.
- **The service worker.** The API and auth paths are excluded before
  anything else is considered, non-GET and cross-origin pass through,
  and what may be cached is an allowlist rather than a denylist.

One rule is open by its own note: tool output is not yet fenced and
labelled as data before it reaches the model. The memory file now is;
tool results are the larger remaining surface of the same kind.

## The tool-output fence had one spelling

Every result from an outside server is wrapped in a marker and preceded
by a line saying the text inside is data to read and not instructions to
follow. The wrapper already neutralised the marker when the content
carried it, so a ticket could not close its own fence.

It neutralised one spelling. `<<<external-content>>>` was caught and
`<<<EXTERNAL-CONTENT>>>` was not, so a result carrying the second ended
its fence and everything after it sat outside, unmarked, reading as the
agent's own instructions.

This is the same hole the memory fence had, found the same way and
fixed the same way: the match is now case-insensitive and tolerant of
spaces inside the marker. A strict comparison and a lenient reader are
one hole with a longer payload, and the reader is the thing being
protected. The source name is fenced too — it is interpolated one line
above the content, which is the same hole one line higher.

Content is replaced rather than removed, with something that says it
was escaped. A silent rewrite of a server's words is its own kind of
wrong: somebody comparing an answer against the record it came from
needs to see that it happened.

### And a sentence in the standing instructions

The per-result line arrives beside the content, in the same part of the
turn the content occupies, so a model weighing two adjacent claims about
which text to trust has been handed a coin to flip. The standing
instructions are written by the deployment, sit above everything any
server said, and nothing in a ticket can reach them.

It says what to *do* about an instruction found inside, not only that
the text is data. Told only the latter, a model asked to follow
something has no rule to apply and complies; told that such an
instruction is evidence the content is hostile and worth reporting, it
has somewhere to go.

It appears only where something can produce fenced output. A paragraph
on every deployment regardless of whether it applies is one the model
learns to skim, which costs it on the deployment where it mattered.

What is still open is the part that does not depend on the model
reading carefully: a write that follows an untrusted read should ask,
whatever its own policy says. Labelling raises the cost of an
injection; it does not stop one.

### A write after an untrusted read now asks

The fence is only as good as the model honouring it, which is the thing
an injection is trying to subvert. So there is a second rule that does
not depend on the model at all: once a run has read text from outside,
a tool that changes something is put to a person before it acts,
whatever its own policy says.

A tool that does not declare whether it writes escalates too. That is
the opposite of the usual unknown-means-permitted rule, deliberately: a
tool nobody annotated is a tool nobody thought about, and the default
should not be generous once something hostile may be steering.

Held per run, in a context variable, and forgotten at the run boundary
by a middleware whose only job that is. Carried across runs, the first
injection anybody ever triggered would make every later run prompt for
ever — and people would learn to approve without reading, which is
worse than not asking.

The question names the write and, where a line of what was read turns
up in the arguments, quotes it back. "Approve this write" tells
somebody nothing; "it repeats *deploy is blocked on the migration*,
which came from the ticket you just read" is the whole decision.

Matching is per line as well as per whole result, because a line is
what gets echoed: a comment quotes a sentence from a ticket, not the
ticket. Recorded only whole, the ledger found nothing in the ordinary
case and the question fell back to "this run read something" — true,
and no help. Short lines are not kept: a fragment of a few characters
appears in almost any text, and a question that always quotes
something teaches people to approve without reading.

Still coarse, and still only the decision. Carrying it into the
approval interrupt itself, so the run actually stops, is the next
piece.

### Carrying the decision to a person

The rule decided and nothing acted on it: a run could read a ticket,
conclude a following write should be asked about, and make the write
anyway.

The approval machinery cannot express this itself. Which tools
interrupt is fixed when the graph is built, and this depends on what
happened during the run, so the question is raised from the tool
wrapper — the same place the authorization interrupt already comes
from, using the same payload shape, so it appears as the approval
somebody already knows rather than a second kind of prompt.

**Only where the policy says allow.** A tool already set to *ask* will
be interrupted by the existing machinery, and raising a second question
for the same call asks somebody twice for one decision — a pair of
approvals is how the second one stops being read. A tool already
refused is not going to run, so there is nothing to ask.

A consequence worth stating: on a deployment that already asks about
everything, this rule changes nothing. It earns its keep where a write
tool was deliberately permitted outright, which is the case nobody was
guarding.

**Inside a subagent it refuses instead of asking.** A subagent is not a
conversation; pausing there stops a graph nobody is watching, the
parent run ends interrupted, and the person sees the agent stop for no
stated reason. That failure is already on record here for the
authorization case, and this rule would have reproduced it exactly. The
write still does not happen — which is the part that matters — and the
orchestrator gets a sentence it can relay.

**What the quoting can and cannot do.** Where a line of what was read
turns up in the arguments, the question quotes it. A result that
arrives as a single line only matches a write reproducing that line in
full, so an echo with a prefix in front of it — *Per the ticket: …* —
asks without a quote. The question is still raised; it is the coarser
wording, which is honest about what was established.

### The reason was being thrown away by the interface

The agent sends a sentence with every approval saying why it is being
asked. The approval card rendered the tool's name, its arguments and
two buttons, and dropped the sentence — the type it parses did not even
have the field.

So the escalation above produced a card indistinguishable from every
routine approval, which is the failure the sentence exists to prevent:
identical cards are the ones people click through. The framework's own
default explanation was being discarded the same way.

The card now shows it, and shows nothing where there is none. A tool
whose policy always asks needs no explanation — the answer to "why am I
being asked" is "you always are" — and a sentence under every card is
one people stop reading, which costs the card that had something to
say.

### Content could forge the label, if not the fence

Three injection shapes were checked against the wrapper: a direct
instruction, one inside a code block, one inside a URL. All three are
ordinary text as far as the fence is concerned, and it held around each
without altering the content.

A fourth is aimed at the wrapper rather than at the reader. A result
can contain the sentence the wrapper writes above it — *The following
is data retrieved from …* — and name a source it prefers. The marker
still held, so nothing escaped the fence; but a model reading a second,
inner preamble claiming the text came from the deployment's own
configuration has been handed a reason to trust what follows. The fence
stayed shut and the label lied.

That opening is now neutralised in content the same way the marker is,
so only one label in the block is the wrapper's. Defanged rather than
deleted — the words stay legible, prefixed by an explicit escape — on
the same reasoning as everywhere else here: a fact removed silently is
reported as the agent losing information, and the person who wrote it
cannot tell which happened.

The phrase is specific enough that ordinary prose does not trip it. "The
following is data we collected last quarter" is untouched, and so is a
runbook sentence about ignoring previous instructions. Both are pinned
by tests, because a guard that mangles innocent text gets switched off.

### An answer now names what it repeated from outside

An answer built out of a ticket reads exactly like one built out of
what the agent knows. The reader can judge the ticket — open it, know
the team, perhaps have written it — but only if they are told it is in
there.

This matters most where the content was hostile. An injected
*instruction* the agent reports rather than obeys is a good outcome; an
injected *claim* the agent repeats as fact is not, and nothing about
the sentence gives it away.

The lines that came from outside were already recorded for the write
rule, so this asks which of them turn up in the answer and writes the
servers onto the turn. Named once each however often quoted, and
nothing at all when nothing matched — an empty list reads as "checked
and found none", a different claim from "did not need to look".

Short lines are excluded, as everywhere else here: a fragment of a few
characters appears in almost any sentence, and an attribution under
every answer is one nobody reads on the answer that needed it.

The interface says it separately from the citations strip above it.
Citations name documents this deployment keeps; this names a third
party, which is a different claim and deserves different words.

**A deployment's own document library is not "outside".** It goes
through the retrieval tool rather than the external-server wrapper, so
it is cited as *your documents* and not flagged here. That is the right
split, and it is why this cannot be demonstrated on a local setup with
no connected third-party server.

## The tool ceiling dropped what it promised to keep

Shortlisting narrows the tools offered on a turn. Two are never
narrowed away: a tool this run has already called — a resumed run must
answer a call the graph before it made, and a dropped tool leaves that
result with nowhere to land — and the placeholder an unconnected server
contributes, which is how it becomes something a person can connect.

The selection honoured both. The ceiling then undid it: the protected
tools were sorted to the front and the whole list truncated, so a run
with more protected tools than the ceiling allows lost the surplus.
Silently, and precisely the failure the sorting was written to prevent.
The comment above it said a ceiling that drops a checkpointed call
turns a resumable run into a broken one, which is what the code did.

A ceiling is a preference about cost; what must survive is a
correctness rule. When they disagree the rule now wins and the list
runs long — which is what the sibling implementation of this same idea
already did, and the disagreement between the two is how this went
unnoticed.

Running long is a concession to the rule, not a licence to ignore the
ceiling: nothing unprotected rides along with the overflow, and a
pinned pattern is treated as a deployment's decision on the same
footing as a checkpointed call.

### Two ways the untrusted-read record could have been lost

Once a run has read text from outside, a following write is put to a
person. That decision is only as good as the record it rests on, and
there are two ways to lose that record without anybody noticing. Both
were checked; both hold; both are now pinned, because a silent
failure here looks exactly like the rule never applying.

**A subagent.** Subagents build their own middleware list. Adding the
run-boundary reset to it would clear the parent's record the moment
work was delegated — and delegating is the common case for precisely
the long, tool-heavy runs where something hostile is most likely to
have been read. The subagent list does not contain it, and a test says
so; a second test says the orchestrator's list does, because two lists
both lacking it would otherwise pass quietly.

**Compaction.** A long thread gets summarised. If the record lived in
the messages, summarising the span that carried it would re-enable
writes an untrusted read had escalated. It lives in a context variable
instead, and the question that reads it takes no arguments — a
function with nothing to pass it cannot be changed by summarising
anything.

The library's own compactor already refuses to split a tool call from
its result, which is the other invariant this area depends on, so
there is no second compactor here. A parallel implementation of a rule
is how three of this session's bugs happened.

## A loop that optimises for success will remove the block

The improvement loop reads an agent's own runs and proposes
configuration changes. It optimises for tasks succeeding, and the
cheapest way to make a blocked task succeed is to remove the block:
widen an approval policy, drop a deny rule, vouch for one more server,
raise a budget.

A proposal that does any of those is now refused by the thing
generating it, not caught by whoever reviews it. A reviewer who
approves fifty sensible diffs will approve the fifty-first, and the
fifty-first is the one that mattered. That is review fatigue, and it is
not a control.

What counts as loosening:

- an approval decision moving towards permissive, in any of its
  spellings — `deny` to `ask`, `ask` to `allow`, `deny` to `allow`;
- a deny rule removed, which is the same thing by deletion;
- a server added to the vouched-for list, since a vouched server's
  output is not fenced and adding one turns somebody else's text back
  into text the agent may follow;
- fencing switched off entirely;
- any cap raised or removed.

Everything else is fair game. A prompt, a tool description, a
retrieval setting — none of them lets the agent do something it could
not do before, and treating them as controls would refuse every useful
proposal this loop exists to make.

Two deliberate asymmetries. On a control, "cannot tell" means no: a cap
whose new value will not parse is refused rather than waved through,
because a cap nobody can compare is a cap nobody can say is still in
place. On everything else, unknown means permitted, or every prompt
edit would be refused.

Refusals name every objection, not the first. Fixing one and
resubmitting, three times, is how a reviewer stops reading.

The generator this guards is not built. The rule is reachable now
anyway, from the command line, because a check that arrives with the
feature arrives after the first proposal has already been written
against no rule at all.

## No route builds a credential into a response

Secrets reach this system to be used, not to be read. A route that
echoes one back copies it somewhere unprotected — a browser cache, a
screenshot, a support bundle, a log of the response — and nobody
involved thinks of themselves as having handled a secret.

The usual defence is remembering to redact each new field, which works
until somebody adds a field. So every route module is read: 31 of them,
326 response keys, and none shaped like a credential. Saying a secret
is *present* — `has_api_key` — is allowed, because that is how a
settings page shows something is configured without showing it.

Two things this is not, both learned by building the wrong version
first.

**It does not call the routes.** The first version asked each one over
HTTP, which meant waiting on a database that is not running: five
minutes for a single test file, and an answer that depended on what
happened to be up. A check that slow is one people stop running, and
then it guards nothing. The same mistake had just been made in the
orphan sweep, which took ninety-eight seconds before it was fixed.

**It does not look at keyword arguments.** That version flagged
`verify(secret=secret)` — a credential being handed to a signature
check, which is the correct thing to do with one. A guard that fires on
correct code is a guard somebody deletes.

Model classes are read too. A response declared as a class carries no
dictionary keys at all, and twenty-one of them live in these modules —
a large blind spot to leave behind a passing test. Fifty annotated
fields are now covered alongside the 326 keys.

Every class with annotations is read, not only those named like a
response. A model used for both a request and a reply is the ordinary
case, and guessing from the name is how one gets missed.

**The sweep is shown to fail.** Five planted modules — a token in a
dictionary, a token on a model class, one nested inside another
response, and two presence flags that must be allowed — prove the rule
catches what it claims and leaves alone what it should. A green sweep
on its own says nothing: a rule that quietly matches nothing looks
exactly like a codebase with no leaks.

## An in-process extension has the agent's privileges

A deployment may name its own middleware in configuration and the agent
imports it. That code then runs inside the agent: it can call anything
importable, including the functions holding the untrusted-read record
and deciding whether a write is put to a person.

There is no sandbox, and none is possible for code imported into the
same process. The requirement this answers asks for tests proving an
extension cannot approve a call, widen a scope, read a credential or
clear the untrusted flag. **On the in-process path none of those can be
prevented** — only an out-of-process runner can give that boundary, and
it is not built.

Saying otherwise would be the worst outcome available: somebody reads a
reassuring sentence, declares an extension from a tree they do not
fully control, and believes in a boundary that is not there.

What is true, and now tested:

- an extension cannot arrive unnoticed — every load is logged;
- it cannot arrive unnamed — the line carries the import path, because
  "loaded 3 extensions" tells a reviewer nothing they can act on;
- one declared required and unable to load stops the agent, rather
  than leaving a compliance check that passes everything silently;
- unmarked means required, since an extension nobody thought to
  classify is likelier to be a check than a flourish.

All four are detection, not prevention, and the difference is the
point.

There are also tests asserting the privilege *exists* — that the loader
imports into this process, and that the untrusted-read record is
reachable from anything. They will fail the day somebody builds the
out-of-process runner, and should then be replaced by tests of the real
boundary. A failing test is a better prompt than a comment nobody
reads.

## Where a secret lives is now a setting

Every secret here was named by the environment variable holding it, and
every site that needed one read it itself. That works, and it means a
deployment whose security team keeps secrets somewhere else has to copy
them into the environment first — the copy nobody wanted to make.

There is one resolver now. A bare name still means the environment, so
no configuration file changes and a deployment that does nothing
behaves exactly as before. A reference that names a source — `env:NAME`
today, something else later — resolves through the same path, and the
call sites need no change to follow it.

Three rules live here rather than at every call site.

**A value never appears in a message.** Not in a log line, not in an
error, not in a tool result. A failure that quotes the secret has moved
it somewhere unprotected in the course of complaining it could not be
found.

**Every resolution goes on the audit trail, by reference.** Which
secrets a deployment read, and when, is asked after an incident — and
it is asked of the thing that is retained and queryable, not of
whatever debug logging happened to be switched on that day. The record
carries the reference, the source that answered, and whether anything
was found. It never carries the value.

A failure is recorded as well as a success, and is the more
interesting of the two during an incident. An audit sink that cannot
be written does not cost the run its credential: the trail is a
problem for later, the call is now.

**A failure is loud and names the reference.** `NOT_SET_ANYWHERE is not
set` sends somebody to the right place; a bare "could not start" sends
them reading code. A reference to a source that is named but unbuilt
says so, rather than failing as though the variable were missing.

**Nothing is cached.** A rotated secret is in use on the next call. A
cache outliving a rotation is a deployment still presenting the
credential that was revoked.

An empty variable counts as missing. Set to nothing is the shape a
half-finished deployment leaves behind, and treating it as a value
sends an empty credential to a server, where the failure arrives far
from its cause.

Every site where *configuration* chooses the variable now goes through
it: the OAuth client secret, a channel's signing secret, and an MCP
server's API key. Those are the references a deployment could want to
redirect, so the promise holds for all three.

Two kinds are deliberately left alone.

**Names built by convention.** A subagent's token comes from its own
name — `ASYNC_SUBAGENT_<NAME>_TOKEN` — so there is nothing for a
deployment to redirect, and routing it through the resolver would add
a layer that changes nothing.

**Fixed platform variables.** The single sign-on secret and the rest
are named in code, not in configuration. Pointing those at another
source is a real thing to want and a different change: it needs the
resolver consulted for a name nobody chose.

One rule covers them, in the resolver rather than repeated at each
site: read the variable, and follow it if it points somewhere. Three
sites use it — the token encryption key, its predecessor during a
rotation, and the channel bot token. Writing it again at each one is
how two copies of a rule start disagreeing, which has caused three
separate bugs in this codebase.

It keeps two outcomes apart that look alike. A variable that is
**unset** is nothing, and the caller decides whether that matters. A
variable **set to a reference that cannot be read** raises: the
deployment did configure it, pointed somewhere, and that somewhere did
not answer — a different problem with a different fix. Collapsing them
sends somebody to check a setting that is already correct.

The first version of this did collapse them, and the encryption key
lost its ability to say which had happened. The five outcomes it can
now distinguish:

| What the variable holds | What happens |
|---|---|
| nothing | refused: the variable is required |
| a key | used |
| a reference to something set | resolved and used |
| a reference to something unset | refused, naming what did not answer |
| a reference to an unbuilt source | refused, naming the source |

The token encryption key shows the shape that works for the others. Its variable name stays fixed — a deployment
cannot rename it to reach a key manager — but what the variable
*contains* is a deployment's choice. A raw key still works and is the
common case; a value naming a source is resolved like any other
secret. A key is urlsafe base64 and never contains a colon, so the two
are told apart without a flag.

Nothing about the refusal changes. A key that cannot be reached raises
the same error an unset one does, so the agent still stops rather than
generating one. A generated key unseals nothing the last one wrote: a
deployment that restarted would come back unable to read a single
stored token, and the failure would arrive at whoever pressed Connect
rather than at whoever deployed it.

## One secret doing two jobs, only one of which can rotate

The single sign-on client secret authenticates this agent to the
identity provider. It is also the seed for the key that seals stored
refresh tokens, because it was already there.

Those uses have opposite requirements. A client secret should be
rotatable — most of the point of having one. A key sealing data at
rest cannot rotate unless something re-encrypts what the old one
sealed or keeps the old key around, and this derivation does neither.
Rotate the secret and every stored refresh token becomes unreadable at
once, which was confirmed rather than assumed:

    same secret opens it   -> True
    rotated secret opens it -> InvalidToken

The token encryption key has a previous-key fallback for exactly this
reason. This derivation has no second key to try — its decrypt takes
one secret and that is all.

**So it is deliberately not moved onto the shared resolver, and
deliberately still read once at import.** Those look like oversights
next to the other fixed secrets, which were moved this week, so both
are now pinned by tests. Read per call, a rotation would take effect
silently and immediately: tokens failing to open one at a time,
mid-run, with nothing connecting it to the change. Read once, the
damage at least waits for a restart, where somebody is watching.

The real fix is to stop one secret doing two jobs — a derivation key
of its own, with its own previous-key fallback. That is a migration,
not a refactor, and is not done here.
