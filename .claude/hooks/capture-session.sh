#!/bin/bash
# SessionEnd hook — deterministic capture net.
#
# Summarizes the ending session with a cheap model and drops the result
# into Resources/context/ as an auto-capture signal, so every session is
# guaranteed to leave a trace for the next `consolidate` run. Exits
# silently on empty/mechanical sessions or any error — capture must
# never block session end.
#
# Receives the standard hook JSON on stdin (transcript_path, cwd, ...).

set -u

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
VAULT=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)

[ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ] || exit 0
[ -n "$VAULT" ] && [ -d "$VAULT/Resources/context" ] || exit 0

# Skip trivially short sessions (a transcript with almost no turns).
[ "$(wc -l < "$TRANSCRIPT")" -ge 10 ] || exit 0

# Pull user and assistant text out of the JSONL transcript, capped so the
# summarizer call stays cheap even after very long sessions.
CONTENT=$(jq -r '
  select(.type == "user" or .type == "assistant")
  | .message.content
  | if type == "array" then (map(select(.type == "text") | .text) | join("\n"))
    elif type == "string" then .
    else empty end
' "$TRANSCRIPT" 2>/dev/null | head -c 60000)

[ -n "$CONTENT" ] || exit 0

PROMPT='You are a memory-capture filter for a knowledge vault. Below is a conversation transcript. Summarize ONLY durable signals worth keeping: decisions made, preferences stated, opinions expressed, priority shifts, and non-trivial new facts about projects, people, tools, or topics the user cares about. Write them as short markdown bullets. If the session was purely mechanical work (routine edits, builds, queries) with no durable signal, output exactly NOTHING_TO_CAPTURE and no other text.'

# Run the summarizer from a neutral cwd: inside the vault it would load
# the vault's own CLAUDE.md and hooks (and re-trigger this SessionEnd
# hook recursively when the headless session ends).
SUMMARY=$(cd "${TMPDIR:-/tmp}" && claude -p --model haiku "$PROMPT

--- TRANSCRIPT ---
$CONTENT" 2>/dev/null)

[ -n "$SUMMARY" ] || exit 0
case "$SUMMARY" in *NOTHING_TO_CAPTURE*) exit 0 ;; esac

STAMP=$(date +%Y-%m-%d-%H%M)
OUT="$VAULT/Resources/context/session-$STAMP.md"
# Don't clobber a capture from another session ending the same minute.
[ -e "$OUT" ] && OUT="$VAULT/Resources/context/session-$STAMP-$$.md"

cat > "$OUT" <<EOF
---
captured: $(date -u +%Y-%m-%dT%H:%M:%SZ)
origin: session-end-hook
---

# Session signals — $STAMP

$SUMMARY
EOF

exit 0
