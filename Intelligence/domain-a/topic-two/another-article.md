---
type: reference
title: Another article — the cost of premature abstraction
description: A bad abstraction is paid for every time a reader has to unwind it, while three duplicated lines are paid for once when someone unifies them.
bundle: domain-a
topic: topic-two
tags: []
source: https://example.com/premature-abstraction
resource: https://example.com/premature-abstraction
timestamp: 2026-05-28T11:25:51Z
status: active
related:
  - domain-a/topic-one/sample-article.md
---

# Another article — the cost of premature abstraction

**Source:** [Notes on the case against premature abstraction](https://example.com/premature-abstraction)
**Author:** A. Engineer
**Captured:** 2026-04-23

---

## Summary

A bad abstraction is paid for every time a reader has to unwind it,
while three duplicated lines are paid for once when someone unifies
them. The right default is to wait for the third occurrence before
abstracting.

## The argument

Each abstraction adds a layer of indirection that every future reader
must traverse. If the abstraction's shape doesn't match the next use
case, callers either branch the abstraction or work around it — both
of which compound the cost (source: clipping-two.md).

The author quotes Sandi Metz: *"duplication is far cheaper than the
wrong abstraction"* (source: clipping-two.md). The implication is
that DRY-at-all-costs is a heuristic past its useful range; the
correct rule is "abstract when you have three concrete cases that
share a shape," not "abstract whenever you see two similar things."

## The inverse failure

The piece notes the inverse failure mode — refusing to abstract
genuinely repeated logic — but argues it is rarer in codebases
written by experienced engineers (source: clipping-two.md). No data
is offered for that "rarer" claim (source: needs-verification).

## Key Takeaways

- The cost of a bad abstraction recurs on every read; the cost of duplication is paid once on unification (source: clipping-two.md).
- "Wait for the third case" is a more useful rule than "DRY everything" (source: clipping-two.md).
- The inverse failure exists but is claimed (without evidence) to be rarer.

## Related

- [[../topic-one/sample-article]] — coordination-overhead framing that cites this article as the counter-source on cause vs proxy.
