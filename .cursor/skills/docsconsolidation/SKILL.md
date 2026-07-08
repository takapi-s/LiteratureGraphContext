---
name: docsconsolidation
description: Consolidate project knowledge into one markdown and keep dev tools outside docs.
---

# Usage

Use this skill when you need to:
- Add or update project knowledge without creating new `docs/*.md` sources-of-truth.
- Keep interactive editors (HTML/JS) out of `docs/`.
- Move or update related references when relocating assets (e.g., IDEA Matrix).

# Single source of truth

The consolidated knowledge is stored in:

- `docs/LGC_KNOWLEDGE_BASE.md`

When new “knowledge” is discovered, append it here under a suitable heading.

# Interactive tools / assets

- Keep interactive HTML/JS editors under `playground/` (or the closest non-`docs/` folder for tools).
- Keep diagrams and static assets referenced from docs under `docs/assets/` (e.g. `docs/assets/idea_matrix.drawio.svg`).
- Update all references (e.g., `ROADMAP.md` image path) whenever an asset path changes.

# When old docs exist

If an existing file under `docs/` becomes redundant:
- Rename it to `*.deprecated.md` (or archive it) instead of deleting immediately if you are unsure.
- Update references to point to the consolidated knowledge file.

# Verification checklist

- `rg` confirms no stale references to moved files remain (e.g. `playground/idea_matrix/idea_matrix.html`).
- `ROADMAP.md` image and edit link point to `docs/assets/idea_matrix.drawio.svg`.

