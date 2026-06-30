# Vault schema — the frozen harness

This file is the **contract** by which the wiki is structured and
judged. It is the autoresearch `prepare.py` analog: read-only to the
agent, edited only by the human.

**The agent MUST NOT modify this file during `consolidate`, `refine`,
or `evaluate`.** Changes to this file are a deliberate human decision
— the equivalent of changing the evaluation harness in autoresearch.
If a verb run requires a schema change to succeed, that's a signal
to stop the run and surface the question to the human, not to edit
the schema.

The agent reads this file once at session start and treats it as
fixed for the rest of the session.

---

## Hard rules

These are non-negotiable. A run that violates any of them is a bug.

1. **`Resources/` is immutable** during read. The only writes are
   post-`consolidate` deletions of sources whose parent folder has
   `delete_after_consolidation: true` (or unset).
2. **`[[wiki links]]` are same-bundle only.** Free across topics
   inside a bundle; **never** across bundles. An article that needs
   to exist in two bundles is duplicated, not linked. This wall applies
   to `[[ ]]` edges *only* — the parallel relative-path / frontmatter
   `related:` channel (see *Article schema*) is the portable OKF graph
   and **may** cross bundles. The `query` walk follows `[[ ]]` only, so
   its same-bundle guarantee is intact.
3. **No silent bundle creation.** Sources matching no existing bundle
   go to `Intelligence/_unsorted/` and surface in the run report.
4. **Topic creation is allowed and expected.** When no existing topic
   in the chosen bundle fits, create one with its `index.md` and
   register it in the bundle's `index.md`.
5. **Images live with their articles.** Every `![[...]]` embed must
   resolve to a file in the same topic folder. No cross-folder image
   references. Duplicating an article into two bundles means copying
   the image into each.
6. **Indexes and log stay in sync, every run.** A `consolidate` that
   touches a bundle must update the topic's `index.md` (always), the
   bundle's `index.md` (if a topic was created), and
   `Intelligence/log.tsv` (always — one append per processed source).
   `Intelligence/index.md` only changes on first-touch of a bundle.
   The `query` verb relies on these indexes being truthful — stale
   indexes silently degrade retrieval, so this is enforced as a hard
   rule, not a courtesy. `refine` flags any drift it finds.
7. **File names are `lowercase-with-hyphens`.** Both folders and
   files. Article slugs match this convention.
8. **Single locus of change.** During a parallel `consolidate` or
   `refine`, each per-bundle subagent writes **only** inside its
   assigned `Intelligence/<bundle>/` subtree. The **orchestrator** is
   the sole writer of `Intelligence/index.md`,
   `Intelligence/log.tsv`, `Intelligence/_unsorted/`,
   `Intelligence/_eval/results.tsv`, and `Intelligence/_episodes/`.
   This eliminates write races and
   matches autoresearch's "one file is the locus of change" principle
   — adapted to a per-bundle fan-out.
9. **Schema is frozen.** This file (`Vault/schema.md`) is read-only
   to the agent. No verb may edit it.

---

## Schemas

Don't paraphrase these. Copy them verbatim when generating files.

### `Resources/<folder>/README.md`

```markdown
---
include_in_consolidation: true     # false → folder is skipped during consolidate
delete_after_consolidation: true   # false → source files stay in place even after successful consolidation
---

# <Folder name>

One paragraph describing what lives here (transcriptions, web
clippings, ideas, etc.) and any handling notes (e.g. "treat each .md
as a single source").
```

The two flags are independent:

- `include_in_consolidation: false` → the folder is dormant input,
  kept for human reference only.
- `delete_after_consolidation: false` → sources are read and
  consolidated, but the originals are **kept** in `Resources/` after
  a successful run. Use this for material with archival value of its
  own (meeting transcriptions, primary documents).
- `delete_after_consolidation: true` → sources are read,
  consolidated, and **deleted** from `Resources/` once `consolidate`
  steps 1–8 succeed. Use for ephemeral material like web clippings.
- Default if either field is missing: `include_in_consolidation: true`,
  `delete_after_consolidation: true`.

### `Intelligence/<bundle>/index.md` (bundle router)

```markdown
# <Bundle name>

**Scope**: One paragraph describing what belongs in this bundle and
what does not. This is the routing signal the agent uses when
allocating new articles.

## Topics

- [[<topic>/index|Topic Title]] — one-line description of the topic cluster
- ...
```

### `Intelligence/<bundle>/<topic>/index.md` (topic router)

```markdown
# <Topic name>

One paragraph describing what this topic clusters.

## Articles

- [[<article-slug>|Article Title]] — one-line description
- ...

## Related Topics

- [[../<other-topic>/index|Other Topic]] — one-line description
- ...
```

`Related Topics` may link to other topics **within the same bundle only**.

### Article schema

Every article opens with a YAML frontmatter block, then the human body.
The frontmatter is the **OKF (Open Knowledge Format) interoperability
surface** — structured, queryable fields that make the article
machine-parseable by agents, the search indexer, Dataview, and any
external OKF consumer. The body is unchanged; frontmatter is additive.

```markdown
---
type: <one of the type vocabulary — see *Article type vocabulary* below>   # REQUIRED
title: <Article title — matches the H1>
description: <one sentence — what this article is and its core thesis>
bundle: <bundle-slug>
topic: <topic-slug>
tags: [tag, tag, …]
source: <primary source path under Resources/, or self-authored>
resource: <live URL of the origin when one exists, else omit/blank>
timestamp: <ISO 8601 UTC of the last consolidate touch>
status: active | needs-verification | deprecated
related:
  - <bundle>/<topic>/<article>.md      # repo-relative; MAY cross bundles (OKF graph)
  - …
---

# <Article title>

**Source:** [<source name>](<url-or-path>)
**Author:** <if known>
**<Other top-of-page metadata as relevant>**

---

## Summary

One short paragraph — what this article is about and the core thesis.

## <Body section>

Body content. Cite each factual claim inline with `(source: <path-or-filename>)`.

Embed images with `![[image.png]]`. The image file must live in the
same topic folder as the article — see *Image handling* below.

## Key Takeaways

- ...

## Related

- [[<other-article-in-this-bundle>]] · [<title>](../<topic>/<article>.md) — one-line note
```

**Required frontmatter key:** `type` (the only mandatory field, mirroring
OKF). All other keys are recommended but optional; a missing `type`
counts toward **schema-violations** drift. The body's `**Source:**` line
and inline `(source: …)` citations are **retained** — the *Citation
rules* are unchanged. `source`/`resource` duplicate provenance in a
queryable field; the inline citations remain the per-claim record.

**Dual-link channel.** The `## Related` block keeps the Obsidian
`[[wiki link]]` (same-bundle only, hard rule 2) **and** adds a
relative-path markdown link beside it, so both a) Obsidian's graph and
the `query` walk and b) an external OKF consumer outside Obsidian can
traverse. The frontmatter `related:` array is the canonical
machine-readable edge list and **may cross bundles** (the portable OKF
graph). See *Cross-bundle links* under *Drift count*.

### Article type vocabulary

`type` is the only OKF-required field and takes any string — OKF
prescribes **no** taxonomy (its `Table`/`Metric`/`Runbook` examples are
illustrative of one producer's data catalogue, not a fixed enum). Define
your own vocabulary that fits your bundles. A reasonable starter set:

| `type` | Use for |
|---|---|
| `reference` | evergreen, factual reference articles (a sensible default) |
| `synthesis` | distilled multi-source write-ups |
| `note` | short atomic notes |
| `digest` | date-keyed daily/periodic summaries |
| `profile` | identity / personal-context articles |

`consolidate` defaults `type` from the bundle (default per the table above), and may override per-article
when a more specific type fits. An unrecognised `type` value is not a
drift violation (OKF treats it as an opaque facet).

---

## Citation rules

These apply to every article body. They are part of the schema, not
a suggestion.

- **Every factual claim references its source file.** No bare claims.
- **Format: `(source: filename.pdf)`** (or `.md`, `.html`, etc.)
  **after the claim**, inline. Not as a footnote, not at section end.
- **If two sources disagree, note the contradiction explicitly** in
  the article body. Example: *"Source A says X (source: a.md);
  source B says Y (source: b.md) — unresolved."* `consolidate`
  surfaces contradictions inline; `refine` reports them.
- **If a claim has no source, mark it `(source: needs-verification)`**
  so `refine` can pick it up. Never invent a source path to silence
  this rule.

---

## Image handling

When a source file references an image (or the article body needs
one):

1. Locate the image in `Resources/` (it should sit beside the source
   file that references it).
2. **Copy** the image file into the article's topic folder
   (`Intelligence/<bundle>/<topic>/`). Don't link out to `Resources/`
   — articles must remain self-contained so deleting the source after
   consolidation doesn't break embeds.
3. Reference the image with `![[image-filename.ext]]` — Obsidian
   resolves it from the same folder.
4. If the same image is referenced by articles in two different
   topics (or two bundles) during a duplication, copy it into each
   topic folder. Storage cost is trivial; the self-containment
   property matters more.

When a source is deleted post-consolidation, its referenced images
are deleted alongside it. When a source is kept, its images stay too
— the topic folder already has its own copy from step 4 of
`consolidate`.

---

## Log format — `Intelligence/log.tsv`

Tab-separated, fixed columns. Header row is line 1. One append per
processed source for `consolidate`; one summary row per run for
`refine` and `evaluate`.

Columns (9, in order):

```
timestamp	verb	source	bundle	topic	articles_changed	images_copied	status	notes
```

- `timestamp` — ISO 8601 UTC (`2026-04-26T14:32:01Z`).
- `verb` — `consolidate` | `refine` | `evaluate`.
- `source` — path under `Resources/` for `consolidate` rows;
  `(refine)` for refine summary rows; `(evaluate)` for evaluate
  summary rows.
- `bundle` — the bundle touched, `_unsorted` for quarantine,
  `(all)` for cross-bundle summary rows, empty if not applicable.
- `topic` — the topic touched, empty if not applicable.
- `articles_changed` — integer count (written + updated).
- `images_copied` — integer count.
- `status` — `kept` | `quarantined` | `crashed` | `refine_summary`
  | `eval_summary` | `episode_captured` | `reflect_summary`.
- `notes` — short freeform. For `refine_summary` rows, **must
  include** `drift=<N>` where N is the total drift count
  (orphans + index-mismatches + broken-embeds + cross-bundle-links
  + schema-violations + episode-integrity). For `eval_summary` rows,
  **must include** `total_files_read=<N>` and
  `quality=<good>/<partial>/<poor>/<missing>` counts
  (e.g. `quality=3g/1p/1m`), and **should include**
  `recall_reads=<N>` and `quarantine_rate=<k>/<n>` so the
  self-improvement trend is visible. For `reflect_summary` rows,
  **must include** `episodes=<N>` (episodes scanned) and
  `reflections=<N>` (reflection lines after the merge). For
  `episode_captured` rows, the `source` column carries the episode
  path and `notes` is a one-line situation.

**Never use commas as separators.** Tabs only — commas appear in
freeform `notes`.

---

## Eval results format — `Intelligence/_eval/results.tsv`

Tab-separated, fixed columns. Header row is line 1. One append per
question per `evaluate` run.

Columns (5, in order):

```
timestamp	question_id	files_read	answer_quality	notes
```

- `timestamp` — ISO 8601 UTC.
- `question_id` — `q1`, `q2`, …, matching IDs in
  `_eval/questions.md`.
- `files_read` — integer count of files the agent had to `Read` to
  answer (excludes `index.md` router reads at any level
  reads — those are routing overhead, not retrieval cost). The
  primary metric — the closest analog to autoresearch's `val_bpb`.
  Lower is better.
- `answer_quality` — `good` | `partial` | `poor` | `missing`.
  Self-judged by the agent against the question's intent.
- `notes` — short freeform. Note any cross-topic walks, any reliance
  on `(source: needs-verification)` claims, any quarantine hits. When
  episodic recall contributed to the answer, **include
  `recall_reads=<N>`** — the count of episode *bodies* read during
  recall. This is tracked **separately from `files_read`** (which
  stays the pure wiki-retrieval metric, so its historical baseline
  remains comparable). `recall_reads` is bounded by the recall budget
  `k` (see *Episodic memory contracts*).

---

## Drift count — what `refine` measures

A single integer. Sum of:

- **Orphans** — articles with zero inbound `[[wiki links]]` from
  other articles in their bundle (excluding the topic's own
  `index.md` listing).
- **Index mismatches** — entries in any `index.md` router (bundle or
  topic) that don't resolve to a real file, or files on disk not
  listed in the relevant index.
- **Broken embeds** — `![[image.ext]]` references that don't resolve
  in the same topic folder.
- **Cross-bundle links** — any `[[wiki link]]` that crosses bundle
  boundaries (hard-rule-2 violation; counts as a single drift unit per
  occurrence). **Relative-path markdown links and the frontmatter
  `related:` array are exempt** — they are the intended portable OKF
  graph channel and may cross bundles freely. Only `[[ ]]` edges are
  walled; the query walk follows only `[[ ]]`, so its same-bundle
  safety is preserved.
- **Schema violations** — articles missing required sections
  (`Source:`, `Summary`, etc.), factual claims without
  `(source: ...)` citations, or **a missing required `type` frontmatter
  key**. (Other frontmatter keys are optional; an unrecognised `type`
  value is not a violation.)
- **Episode integrity** — episodes in `Intelligence/_episodes/`
  missing required frontmatter or sections (see *Episodic memory
  contracts*), or any `[[wiki link]]` inside an episode that points
  **outside** `_episodes/` (episodes reference bundle articles by
  `(source: ...)` citation only — a `[[ ]]` edge leaving the zone is
  a violation, counted once per occurrence). Episode→article
  citations are **not** counted (they are not link-graph edges).

**Advance-on-improvement rule:** the orchestrator compares the
current `refine_summary` row's drift count to the previous one (last
`refine_summary` row in `log.tsv`). It reports the delta as
**advance** (drift down, or drift flat with `articles_changed > 0`),
**hold** (drift flat with `articles_changed == 0`), or **regress**
(drift up). The orchestrator never silently undoes work — humans
decide what to do with a regression report.

---

## Episodic memory contracts

`Intelligence/_episodes/` is the **episodic** memory zone — the
agent's record of *experiences* (goal → actions → outcome → insight),
distinct from the semantic facts held in the bundles. It is a
governance zone like `_eval/` and `_unsorted/`: **not** a bundle, so
the `query` bundle-walk ignores it, and the orchestrator is its sole
writer (hard rule 8). These schemas are frozen — copy them verbatim.

### Zone layout

```
Intelligence/_episodes/
  _index.md            # thin router: the three kinds + tag vocabulary, no bodies
  operational/         # the agent's own verb runs
    _index.md
    operational-<verb>-<iso-timestamp>.md   # filename = episode_id
  life/                # derived from Resources/Daily/ digests
    _index.md
    life-<date>.md                          # filename = episode_id
  signals/             # derived from Resources/context/ auto-capture drops
    _index.md
    signal-<slug>.md                        # filename = episode_id
  reflections.md       # distilled, MERGED generalized patterns
```

**Filename rule (resolvability):** an episode file is named exactly
`<episode_id>.md` (kind-prefixed), so a kind-index one-liner that lists
`<episode_id>` resolves directly to `<kind>/<episode_id>.md`. Recall
depends on this — do not drop the kind prefix from the filename.

### Episode schema — `_episodes/<kind>/<id>.md`

```markdown
---
episode_id: <kind>-<iso-timestamp-or-slug>
kind: operational | life | signal
verb: consolidate | query | refine | evaluate    # operational only; omit otherwise
timestamp: 2026-06-02T10:05:00Z
situation: <one line — the context/inputs>
intent: <one line — the goal of this episode>
outcome: success | partial | failure
tags: [bundle-or-topic, source-type, …]          # the recall index
distilled: false                                  # reflect sets true once folded into reflections.md
---

## Situation
Context and inputs. operational: which sources / which question.
life: the day in one paragraph. signal: what was captured and why.

## Actions
What was done, in order. operational: per-source routing decisions
(bundle→topic, why), articles read/written, quarantine calls.
life/signal: the decision/preference recorded (often N/A).

## Outcome
Result + concrete evidence. operational: kept/quarantined counts,
eval quality, drift delta. life: decisions, open loops. signal: the
stated preference/decision.

## Insights
The generalizable nugget — effective approaches and pitfalls. This is
what `reflect` later distills.

## Links
`[[related-episode]]` **within `_episodes/` only**, and
`(source: <path>)` citations to origin sources and related bundle
articles.
```

Required frontmatter keys: `episode_id`, `kind`, `timestamp`,
`situation`, `intent`, `outcome`, `tags`, `distilled`. Required
sections: `Situation`, `Actions`, `Outcome`, `Insights`. Missing
keys/sections count toward **episode integrity** drift.

### Kind-index schema — `_episodes/<kind>/_index.md`

```markdown
# <Kind> episodes

One line describing what this kind captures.

## Episodes

- `<episode_id>` | tags: a, b | <one-line situation> | <outcome> | distilled: <bool>
- ...
```

One line per episode — `id | tags | situation | outcome | distilled`.
Bodies are never inlined here; this is the routing surface recall
scans before pulling ≤`k` bodies.

### Reflection schema — `_episodes/reflections.md`

A flat list of distilled, generalized heuristics, each citing the
episodes it was drawn from. `reflect` **rewrites** this file (merge,
not append) so it stays small as the episode store grows.

```markdown
# Reflections

Distilled patterns across episodes. Generalized guidance, not
step-by-step. `reflect` merges and rewrites this list; it never
appends unboundedly.

- **<category>:** <generalized heuristic>. (episodes: <id>, <id>)
- ...
```

### Recall budget and the linking rule

- **Recall budget `k = 3`.** A recall walk reads at most **3 episode
  bodies** (exemplars), plus the whole `reflections.md` (kept small
  by merging). Cost ≈ 1 router + 1 kind-index + ≤3 bodies +
  `reflections.md` — bounded, not growing with the store. Same spirit
  as the `query` budget ceiling.
- **`distilled: true` episodes are excluded from the default exemplar
  walk** — their insight already lives in `reflections.md`. They stay
  on disk for audit but leave the hot recall surface.
- **Linking rule (preserves hard rule 2).** Episodes reference bundle
  articles by `(source: <bundle>/<topic>/<article>.md)` **citation
  only** — never `[[wiki links]]`. `[[ ]]` links inside episodes are
  **within `_episodes/` only** (episode↔episode). Episodes emit no
  `[[ ]]` edge into a bundle, so the same-bundle-only link firewall is
  untouched. Bundle articles never link back to episodes (one-way).
