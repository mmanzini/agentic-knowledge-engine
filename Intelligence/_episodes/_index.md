# Episodes — episodic memory

The agent's record of **experiences** (goal → actions → outcome →
insight), distinct from the **semantic** facts held in the bundles.
This is a governance zone like `_eval/` and `_unsorted/` — not a
bundle. The `query` bundle-walk ignores it; episodic **recall** is a
separate, bounded retrieval path. The orchestrator is the sole writer.

See *Episodic memory contracts* in [schema.md](../../schema.md) for the
frozen schemas, the recall budget, and the linking rule. See the
`## Episodic memory` section in [CLAUDE.md](../../CLAUDE.md) for the
recall → act → capture wiring and the `reflect` verb.

The episodes below are **placeholders** demonstrating the schema —
replace them as your own runs accumulate.

## Kinds

- [[operational/_index|Operational]] — the agent's own verb runs
  (`consolidate`/`query`/`refine`/`evaluate`). Improves how the agent
  curates and retrieves over time.
- [[life/_index|Life]] — derived from `Resources/Daily/` digests (add a
  `Resources/Daily/` folder if you keep date-keyed notes). Makes past
  days recallable as personal context.
- [[signals/_index|Signals]] — derived from `Resources/context/`
  auto-capture drops (decisions, preferences, reactions).

## Reflections

- [[reflections|Reflections]] — distilled, merged generalized patterns
  across all episodes. The compressed layer recall leans on as the raw
  store grows.

## Tag vocabulary

Tags are the recall routing signal (the kind-index one-liners + each
episode's frontmatter `tags`). Keep them aligned with your bundle/topic
slugs so recall can match a task to past experience. Seed vocabulary
(extend as the store grows):

- **bundle/topic tags** — mirror your bundle and topic slugs
  (e.g. `domain-a`, `topic-one`).
- **source-type tags** — `daily-digest`, `auto-capture`,
  `web-clipping`, `transcription`.
- **outcome tags** — `quarantine`, `new-topic`, `multi-bundle`.
