# Evaluation question set

Fixed questions used by the `evaluate` verb to measure whether the
wiki is getting better at answering things the user actually cares
about. **This is the wiki's `val_bpb` analog** — without a
representative question set, "did the wiki improve?" is unmeasurable
and the autoresearch discipline collapses into a vibe.

**Replace these placeholders with your real questions.** The seeded
five target the placeholder bundles and span the access patterns the
wiki must support: single-topic retrieval, within-bundle cross-topic
retrieval, and cross-bundle distinction. Their value is illustrative
— rewrite them once you know what you actually want this vault to
answer.

The verb spec for `evaluate` lives in [CLAUDE.md](../../CLAUDE.md);
the row schema for results lives in [schema.md](../../schema.md).

## Questions

### q1 — single-topic retrieval (Domain A)

**Prompt:** What is the argument for small teams shipping faster
than large ones?

**Target topic:** `domain-a/topic-one`. Tests that a query for a
single-topic question reads only that topic's articles, not its
neighbours.

**Expected file_read budget:** 1 article body.

### q2 — single-topic retrieval (different topic)

**Prompt:** When is duplication preferable to abstraction, and why?

**Target topic:** `domain-a/topic-two`. Tests routing within a
bundle: the answer should come from `topic-two`, not `topic-one`.

**Expected file_read budget:** 1 article body.

### q3 — within-bundle cross-topic retrieval

**Prompt:** Is team size the cause of coordination cost, or merely
a proxy?

**Target topics:** `domain-a/topic-one` ↔ `domain-a/topic-two`.
Tests that the agent follows `[[wiki links]]` across topics inside
a bundle when the answer requires synthesising both. The article in
`topic-one` notes the contradiction with `topic-two`'s framing
explicitly — a `good` answer should reference both.

**Expected file_read budget:** 2 article bodies.

### q4 — different-bundle detail recall

**Prompt:** What blocks platform teams from automating credential
rotation?

**Target topic:** `domain-b/topic-three`. Tests that the agent
correctly routes to the second bundle and doesn't mis-route to
Domain A's operational-sounding articles.

**Expected file_read budget:** 1 article body.

### q5 — citation-based reasoning

**Prompt:** Do the available sources address whether secret rotation
is primarily a tooling problem or a political one? If so, on what
basis?

**Target topic:** `domain-b/topic-three`. Tests that the agent reads
the citations carefully, surfaces the single-source caveat
(`(source: needs-verification)` for the "how representative this is"
claim), and doesn't overclaim. A `good` answer cites the
political-blocker reasoning AND notes the evidence is one
interview.

**Expected file_read budget:** 1 article body.

### q6 — generative task with mandatory personal-context auto-pull (TEMPLATE)

**Prompt:** *Replace this with your own generative-task question
that should force the agent to walk a personal-context bundle
(e.g., a bundle sourced from `Resources/personal/about-me.md` and
`writing-rules.md`) BEFORE generating.* Example:
"Draft a short LinkedIn post (≤120 words) introducing this project
in my voice — what it is, why it exists, what makes it different."

**Target topics:** the personal-context bundle (e.g.,
`personal/_master-index` and articles inside it). A `good` answer
reads those articles **before** generating, and the resulting output
matches the user's stated voice (no marketing fluff, no AI-writing
tells).

**What this tests:** the personal-context auto-pull behaviour
described in `query` step "Personal context auto-pull". This is a
**generative** task — the trigger is the task type, not the user's
wording. The agent must walk `personal/` proactively. Skipping it
is a regression even if the output sounds plausible.

**Tracking:** in `_eval/results.tsv` `notes`, record
`personal_pulled=yes expected=yes`. A `good` quality requires
`personal_pulled=yes`; `personal_pulled=no` downgrades to `poor`
regardless of content quality.

**Expected file_read budget:** 2–3 article bodies (all from the
personal-context bundle).

### q7 — boundary case: pure technical query, no personal walk expected (TEMPLATE)

**Prompt:** *Replace this with your own pure-technical/reference
question that should NOT trigger a personal-context walk.* Example:
"Explain how the `consolidate` verb handles a source file that
matches two bundles at once."

**Target topic:** any technical/reference topic in your wiki — not
the personal-context bundle.

**What this tests:** the **negative side** of the personal-context
auto-pull rule. This is a pure technical/reference question. The
agent must **not** pull `personal/`. Over-pull is a regression
because it inflates `files_read` and conditions answers on
irrelevant context.

**Tracking:** in `_eval/results.tsv` `notes`, record
`personal_pulled=no expected=no`. If `personal_pulled=yes`, downgrade
to `poor` regardless of content quality.

**Expected file_read budget:** 1–2 article bodies (all from the
target technical topic).

### q8 — episodic recall (life / signal) (TEMPLATE)

**Prompt:** *Replace this with a question only answerable from episodic
memory — a past decision or a stated preference, not a semantic fact.*
Example: "What tone preference did I state for drafting, and when?"

**Target:** `Intelligence/_episodes/signals/` (and/or `life/`). Tests
the **recall** path (not the bundle walk): the agent reads
`_episodes/_index.md` → the kind `_index.md` one-liners → pulls ≤`k`
(=3) episode bodies, skipping `distilled: true` ones.

**What this tests:** that experiences are recallable and that recall
stays bounded. A `good` answer cites the episode(s) with
`(source: _episodes/…)` and does not exceed the recall budget.

**Tracking:** in `_eval/results.tsv` `notes`, record `recall_reads=<N>`
**separately** from `files_read` (recall cost is not wiki-retrieval
cost). `recall_reads > 3` is a budget regression.

**Expected file_read budget:** 0 article bodies; `recall_reads` ≤ 2.

### q9 — fuzzy phrasing, tier-2 search expected (TEMPLATE)

**Prompt:** *Replace this with a question about real wiki content,
worded so it shares NO key terms with the relevant index one-liners.*
Example for the placeholder bundles: "Why do big groups slow down
delivery?" (target article says "coordination overhead in software
teams" — zero word overlap).

**Target:** any single article, reached **via tier 2**. Tests the
hybrid-search fallback: the tier-1 walk should miss or stall (the
phrasing matches no index description), the agent should then run
`Intelligence/_search/search.py`, follow the pointer, read the
article, and cite it normally.

**What this tests:** that semantically-phrased questions no longer
dead-end. A `good` answer cites the target article; answering
"not in the wiki" when the article exists is a `missing` —
that was the pre-search failure mode.

**Tracking:** in `_eval/results.tsv` `notes`, record
`tier_used=<0|1|2>`. For this question `tier_used=2` is expected;
`tier_used=1` with a correct answer is fine too (better routing than
predicted), but record it.

**Expected file_read budget:** 1 article body (the search call
itself costs 0).

### q10 — fuzzy phrasing, second target (TEMPLATE)

**Prompt:** *Same shape as q9, different bundle — keeps tier-2
coverage honest across the taxonomy.* Example: "What stops old
access keys from getting cleaned up?" (target article frames it as
"credential rotation" and "political blockers").

**Target / tracking / budget:** as q9 (`tier_used=` in notes,
1 article body).

## How to add a question

1. Append a new section here with an ID (`q6`, `q7`, …), a prompt,
   target topic(s), and an expected file_read budget.
2. Re-run `evaluate`. The new question will get a baseline row in
   `results.tsv`.
3. Compare future runs to that baseline.

Don't remove a question without a reason — the trajectory of a
specific question's read-cost over time is the signal autoresearch
relies on.
