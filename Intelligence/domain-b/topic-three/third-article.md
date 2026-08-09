---
type: reference
title: Third article — secret rotation as political problem
description: 'Long-lived credentials persist not for technical reasons but for political ones: rotation requires breaking external consumers, and platform teams rarely have the air cover to do so on a schedule.'
bundle: domain-b
topic: topic-three
tags: []
sources:
  - id: platform-engineer-interview
    title: Sample transcription — interview with a platform engineer
    resource: Resources/transcriptions/platform-engineer-interview.md
generated:
  by: example-agent/model-v1
  at: '2026-05-28T11:25:51Z'
status: draft
related: []
---

# Third article — secret rotation as political problem

**Source:** Sample transcription — interview with a platform engineer
**Source path:** sample-transcription.md
**Recorded:** 2026-04-15

---

## Summary

Long-lived credentials persist not for technical reasons but for
political ones: rotation requires breaking external consumers, and
platform teams rarely have the air cover to do so on a schedule.

## The toil

The interviewed platform engineer describes secret rotation as the
team's largest source of toil, unchanged across two years of
investment in tooling (source: sample-transcription.md). The team
has a sane secret store, but rotation cadence isn't enforced
anywhere — credentials set up for a feature outlive the feature
indefinitely. They caught one credential last quarter that had been
valid since 2021 (source: sample-transcription.md).

## Why automation alone doesn't solve it

The blocker isn't technical. Automating expiry is straightforward.
The problem is that roughly half the consumers of these credentials
are services the team doesn't own — described as "legacy contractors"
— for which there is no clean rollover story (source:
sample-transcription.md). Forced rotation breaks those consumers.

The team's stated unblocker: a six-month deprecation window with
loud warnings, plus exec air cover when contractor relationships
start escalating (source: sample-transcription.md). The interviewee
is explicit that what's missing is political cover to break things
on purpose, not tooling.

How representative this experience is across other platform teams is
unclear — the article rests on a single interview (source:
needs-verification).

## Key Takeaways

- Secret rotation toil persists despite a working secret store; cadence isn't enforced (source: sample-transcription.md).
- The blocker is unowned downstream consumers, not the rotation mechanism (source: sample-transcription.md).
- The fix is organisational (deprecation window + exec air cover), not technical (source: sample-transcription.md).

## Related

(no within-bundle links yet — this is currently the only article in Domain B)
