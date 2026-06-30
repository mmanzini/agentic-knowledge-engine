---
include_in_consolidation: true
delete_after_consolidation: true
---

# Context (auto-captured)

General-purpose drop folder for the auto-capture skill. Each file is
one signal observed during a conversation — a decision, a priority
shift, a preference, a stated opinion, a reaction, a writing-style
or tone-of-voice observation, a non-trivial new fact about a project,
person, tool, or topic.

The bundle destination is decided at consolidate time by the normal
routing heuristic — captures can land in `personal`, or any other
bundle as appropriate. Multi-bundle placement is allowed when content
fits more than one scope.

The lifecycle here is `delete_after_consolidation: true`: files are
deleted once their value has been transferred into the wiki. To
preserve a capture as a permanent source, **move it into the
appropriate static-source folder** (e.g. `Resources/personal/`)
before the next consolidate run.

Each `.md` is a single source. Filenames follow `YYYY-MM-DD-<slug>.md`.
