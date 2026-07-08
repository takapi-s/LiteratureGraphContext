---
name: knowledgecollector
description: Collect conversation findings into docs/LGC_KNOWLEDGE_BASE.md.
---

# Purpose

When you learn something during a chat (a decision, a lesson learned, a “how to”, a gotcha, or a concrete implementation note), append it to:

`docs/LGC_KNOWLEDGE_BASE.md`

so the repository accumulates knowledge in one place.

# What counts as “knowledge”

- Design decisions and their rationale (including trade-offs)
- Failure modes / gotchas and how to avoid them
- Concrete implementation guidance (paths, commands, tool names, JSON schemas)
- Observations about tool behavior (what worked, what was unstable, what to do instead)

# How to write the entry

1. Pick or create a topic section near the relevant area.
2. Append a new subsection using the existing template style:
   - `YYYY-MM-DD - <topic>`
   - `What we learned / decided:`
   - `Why it matters (trade-offs, failure modes, constraints):`
   - `Where it’s implemented (paths / commands / tool names):`
   - `Verification (what to check / how to reproduce):`
3. Keep it append-only by default (do not overwrite history).
4. If multiple chat messages contain the same idea, deduplicate by summarizing into one entry.

# Guardrails

- Do not create new “source-of-truth” md files under `docs/` for incremental updates.
- When you must move/remove legacy files, update references first, then delete redundant sources.

# Quick verification

- `rg` for old filenames/paths to ensure no stale links remain.
- Re-read the top of `docs/LGC_KNOWLEDGE_BASE.md` to confirm entries are consistent with the single-knowledge-source policy.

