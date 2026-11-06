#!/usr/bin/env bash
# How long the inner loop actually takes (E27-T8, DX-1).
#
# The DX targets are numbers — an agent edit live in under 5s, a UI
# edit under 1s — and a target nobody measures is a sentence in a
# document. This measures the two that matter on the machine in
# front of you and fails when either has drifted past its target.
#
#   scripts/dev/timings.sh              measure, print, exit non-zero on a regression
#   scripts/dev/timings.sh --record     also append to .local/timings.jsonl
#
# It measures against a loop that is already running: starting one
# here would measure the start, which is a different number and the
# one nobody waits for twice.
#
# **It touches a file and puts it back.** The agent reloads on any
# change under its tree, so the probe is a real edit — a comment
# appended to a module and then removed. Nothing else tells you
# what a reload costs, and a synthetic timer would measure the
# timer.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

AGENT_URL="${HARNESS_URL:-http://localhost:5002}"
UI_URL="${UI_URL:-http://localhost:5173}"

# The targets from DX-1. Breaching one is a failure, not a note:
# the loop getting slower is how a team stops using it, and it
# happens one second at a time.
AGENT_TARGET_MS=${AGENT_TARGET_MS:-5000}
UI_TARGET_MS=${UI_TARGET_MS:-1000}

RECORD=0
[ "${1:-}" = "--record" ] && RECORD=1

now_ms() { python3 -c 'import time; print(int(time.time()*1000))'; }

wait_for() {  # url, deadline_ms -> prints elapsed, or nothing
  local url="$1" deadline="$2" start
  start="$(now_ms)"
  while [ "$(( $(now_ms) - start ))" -lt "$deadline" ]; do
    if curl -sf -o /dev/null "$url"; then
      echo "$(( $(now_ms) - start ))"
      return 0
    fi
    sleep 0.05
  done
  return 1
}

fail=0

report() {  # name, measured, target, note
  local name="$1" measured="$2" target="$3" note="${4:-}"
  if [ -z "$measured" ]; then
    printf '%-22s  %s\n' "$name" "${note:-no measurement — is the loop running?}"
    fail=1
    return
  fi
  if [ "$measured" -gt "$target" ]; then
    printf '%-22s  %5sms   SLOW (target %sms)\n' "$name" "$measured" "$target"
    fail=1
  else
    printf '%-22s  %5sms   ok (target %sms)\n' "$name" "$measured" "$target"
  fi
}

# ── the agent's reload ───────────────────────────────────────────
# A real edit to a real module. The file is restored in a trap, so
# a Ctrl-C in the middle does not leave a stray comment in the
# tree — which is the kind of thing that gets committed.
PROBE="services/agent/aegra/health_routes.py"
[ -f "$PROBE" ] || PROBE="$(ls services/agent/aegra/*.py | head -1)"
BACKUP="$(mktemp)"
cp "$PROBE" "$BACKUP"
restore() { cp "$BACKUP" "$PROBE"; rm -f "$BACKUP"; }
trap restore EXIT

# Counted from the loop's own log, which is the only place the
# reload is visible from outside.
#
# Two probes were wrong before this one. "Is /health up" always
# answers, because the reloader keeps the socket while it replaces
# the worker — 96ms, measuring one curl. "Has the pid on the port
# changed" never fires, because that pid belongs to the reloader
# and the worker is a child with a different command line. The log
# line is what the server itself says when it is serving again.
AGENT_LOG="${AGENT_LOG:-.local/logs/agent.log}"
READY="Application startup complete"

# `grep -c` prints 0 *and* exits 1 when it matches nothing, so
# `|| echo 0` fired as well and the function returned "0\n0" for
# an empty log — which `[ ... -gt ... ]` rejects with "integer
# expected" and then treats as not-greater. An agent that had
# started but not yet logged ready therefore measured nothing,
# quietly, which is the blind spot this whole probe exists to
# avoid. Found by `tests/unit/test_timings_probe.py`.
ready_count() {
  n="$(grep -c "$READY" "$AGENT_LOG" 2>/dev/null | head -1)"
  echo "${n:-0}"
}

agent_ms=""
agent_note=""
if [ ! -f "$AGENT_LOG" ]; then
  agent_note="no log at $AGENT_LOG — start the loop with make up"
elif curl -sf -o /dev/null "$AGENT_URL/health"; then
  echo "# a reload probe is being appended to $PROBE and removed again"
  before="$(ready_count)"
  start="$(now_ms)"
  printf '\n# timings probe %s\n' "$(date +%s)" >> "$PROBE"

  while [ "$(( $(now_ms) - start ))" -lt 120000 ]; do
    if [ "$(ready_count)" -gt "$before" ]; then
      agent_ms="$(( $(now_ms) - start ))"
      break
    fi
    sleep 0.1
  done
  [ -n "$agent_ms" ] || agent_note="no reload in 120s — autoreload may be off"
fi
restore
trap - EXIT

# ── the interface ────────────────────────────────────────────────
# Vite serves the edit over its own socket, so what is measured
# here is the dev server answering at all. A hot-module update is
# not visible from outside the browser, and a number that needs a
# browser is a number nobody runs in a terminal.
ui_ms=""
if curl -sf -o /dev/null "$UI_URL"; then
  start="$(now_ms)"
  curl -sf -o /dev/null "$UI_URL" && ui_ms="$(( $(now_ms) - start ))"
fi

report "agent reload" "$agent_ms" "$AGENT_TARGET_MS" "$agent_note"
report "ui response" "$ui_ms" "$UI_TARGET_MS"

if [ "$RECORD" = "1" ]; then
  mkdir -p .local
  printf '{"at":"%s","agent_reload_ms":%s,"ui_ms":%s}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${agent_ms:-null}" "${ui_ms:-null}" \
    >> .local/timings.jsonl
  echo "recorded in .local/timings.jsonl"
fi

exit "$fail"
